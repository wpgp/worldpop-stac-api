"""Collection handling for STAC API."""

import re
from abc import ABC
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import attr
from fastapi import Request
from pymongo.collection import Collection as MongoCollection
from stac_fastapi.types.core import AsyncBaseCoreClient
from stac_fastapi.types.errors import NotFoundError
from stac_fastapi.types.requests import get_base_url
from stac_fastapi.types.stac import Collection, Collections
from stac_pydantic.links import Relations
from stac_pydantic.shared import MimeTypes

from wpstac.db import get_connection
from wpstac.utils import CollectionLinks


@attr.s
class CollectionsMixin(AsyncBaseCoreClient, ABC):
    """Collection operations mixin for WorldPop STAC API.

    This mixin provides methods for retrieving STAC collections from MongoDB,
    with specific handling for country-based collections.
    """

    COLLECTION_ID_PATTERN = re.compile(r'^[a-zA-Z]{3}$')
    DEFAULT_PAGE_SIZE = 10
    MAX_PAGE_SIZE = 100

    def _validate_page_size(self, limit: int) -> int:
        """Validate and normalize page size."""
        if limit < 1:
            return self.DEFAULT_PAGE_SIZE
        if limit > self.MAX_PAGE_SIZE:
            return self.MAX_PAGE_SIZE
        return limit



    @staticmethod
    def validate_collection_id(collection_id: str) -> bool:
        """Validate collection ID format."""
        return bool(CollectionsMixin.COLLECTION_ID_PATTERN.match(collection_id))

    async def all_collections(self, request: Request, **kwargs) -> Collections:
        """Retrieve all available collections."""
        base_url = get_base_url(request)

        page = int(kwargs.get('page', 1))
        limit = self._validate_page_size(int(kwargs.get('limit', self.DEFAULT_PAGE_SIZE)))
        skip = (page - 1) * limit

        async with get_connection(request) as client:
            db = client[request.app.state.settings.mongodb_dbname]
            collection: MongoCollection = db["collections"]

            cursor = collection.find(
                {"id": self.COLLECTION_ID_PATTERN},
                skip=skip,
                limit=limit
            ).sort("id", 1)

            collections = []
            async for item in cursor:
                item["_id"] = str(item["_id"])
                await self._process_collection_links(item)
                collections.append(item)

        total = await collection.count_documents({"id": self.COLLECTION_ID_PATTERN})

        linked_collections = await self._create_linked_collections(collections, request)
        links = await self._create_collection_links(base_url, page, limit, total)

        return Collections(
            collections=linked_collections,
            links=links,
            numberMatched=total,
            numberReturned=len(collections)
        )

    async def _create_collection_links(
            self,
            base_url: str,
            page: int,
            limit: int,
            total: int
    ) -> List[Dict[str, Any]]:
        """Create collection links including pagination.

        Args:
            base_url: Base URL for the API
            page: Current page number
            limit: Items per page
            total: Total number of items

        Returns:
            List of STAC links
        """
        links = [
            {
                "rel": Relations.root.value,
                "type": MimeTypes.json,
                "href": base_url,
            },
            {
                "rel": Relations.parent.value,
                "type": MimeTypes.json,
                "href": base_url,
            },
            {
                "rel": Relations.self.value,
                "type": MimeTypes.json,
                "href": urljoin(base_url, "collections"),
            }
        ]

        # Add pagination links
        total_pages = (total + limit - 1) // limit

        if page > 1:
            links.append({
                "rel": Relations.previous.value,
                "type": MimeTypes.json,
                "href": urljoin(base_url, f"collections?page={page - 1}&limit={limit}"),
            })

        if page < total_pages:
            links.append({
                "rel": Relations.next.value,
                "type": MimeTypes.json,
                "href": urljoin(base_url, f"collections?page={page + 1}&limit={limit}"),
            })

        return links


    async def _process_collection_links(self, item: Dict[str, Any]) -> None:
        """Process collection links."""
        if 'links' in item:
            for link in item['links']:
                if link['rel'] == 'child':
                    link['href'] = link['href'].replace('CODE', item['id'])

    async def _create_linked_collections(
        self,
        collections: List[Dict],
        request: Request
    ) -> List[Collection]:
        """Create linked collections."""
        linked_collections = []
        for c in collections:
            coll = Collection(**c)
            coll["links"] = await CollectionLinks(
                collection_id=coll["id"],
                request=request
            ).get_links(extra_links=coll.get("links"))
            linked_collections.append(coll)
        return linked_collections

    async def get_collection(self, collection_id: str, request: Optional[Request] = None, **kwargs) -> Collection:
        """
        Retrieve a specific collection by its ID.

        This method fetches detailed information about a single STAC collection.

        Args:
            collection_id (str): The unique identifier of the collection.
            request (Request): The incoming HTTP request.

        Returns:
            Collection: A STAC Collection object for the specified collection.

        Raises:
            NotFoundError: If the specified collection does not exist.
        """
        collection: Optional[Dict[str, Any]]

        async with get_connection(request) as client:
            db = client[request.app.state.settings.mongodb_dbname]
            collection_coll: MongoCollection = db["collections"]

            query = {"id": collection_id}
            collection = await collection_coll.find_one(query)

        if collection is None:
            raise NotFoundError(f"Collection {collection_id} does not exist.")

        for link in collection['links']:
            if link['rel'] == 'child':
                country_code = collection['id']
                link['href'] = link['href'].replace('CODE', country_code)

        collection["_id"] = str(collection["_id"])
        collection["links"] = await CollectionLinks(
            collection_id=collection_id, request=request
        ).get_links(extra_links=collection.get("links"))

        return Collection(**collection)
