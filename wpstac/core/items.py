"""Item handling for STAC API."""
from abc import ABC
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import attr
from fastapi import Request
from stac_fastapi.types.core import AsyncBaseCoreClient
from stac_fastapi.types.errors import NotFoundError
from stac_fastapi.types.search import NumType
from stac_fastapi.types.stac import Item, ItemCollection

from wpstac.db import get_connection
from wpstac.utils import ItemCollectionLinks


@attr.s
class ItemsMixin(AsyncBaseCoreClient, ABC):
    """Item operations mixin."""

    DEFAULT_PAGE_SIZE = 10
    MAX_PAGE_SIZE = 1000

    def _validate_page_size(self, limit: Optional[int]) -> int:
        """Validate and normalize page size."""
        if limit is None or limit < 1:
            return self.DEFAULT_PAGE_SIZE
        if limit > self.MAX_PAGE_SIZE:
            return self.MAX_PAGE_SIZE
        return limit

    async def _get_base_item(self, collection_id: str, request: Request) -> Dict[str, Any]:
        """
        Retrieve a base item for a given collection.

        This internal method is used to fetch a representative item from a collection,
        which is then used as a base for hydrating other items.

        Args:
            collection_id (str): The ID of the collection to fetch a base item from.
            request (Request): The incoming HTTP request.

        Returns:
            Dict[str, Any]: A dictionary representing a base STAC Item.

        Raises:
            NotFoundError: If no base item exists for the specified collection.
        """

        item: Optional[Dict[str, Any]] = {}

        async with get_connection(request) as client:
            db = client[request.app.state.settings.mongodb_dbname]
            collection = db['items']
            query = {"collection": collection_id}
            item = await collection.find_one(query)
            if item:
                item["_id"] = str(item["_id"])

        if item is None:
            raise NotFoundError(f"A base item for {collection_id} does not exist.")

        return item

    async def item_collection(self, collection_id: str,
                              request: Optional[Request] = None,
                              bbox: Optional[List[NumType]] = None,
                              datetime: Optional[Union[str,
                              datetime]] = None,
                              limit: Optional[int] = None,
                              token: str = None,
                              **kwargs) -> ItemCollection:
        """
        Retrieve items from a specific collection.

        This method implements the `/collections/{collection_id}/items` endpoint, returning
        items from a given collection with optional filtering.

        Args:
            collection_id (str): The ID of the collection to search within.
            request (Request): The incoming HTTP request.
            bbox (Optional[List[NumType]]): Bounding box for spatial filtering.
            datetime (Optional[Union[str, datetime]]): Temporal filter.
            limit (Optional[int]): Maximum number of items to return.
            token (Optional[str]): Pagination token.

        Returns:
            ItemCollection: A STAC ItemCollection containing the matching items.
        """
        await self.get_collection(collection_id, request=request)

        base_args = {
            "collections": [collection_id],
            "bbox": bbox,
            "datetime": datetime,
            "limit": limit,
            "token": token,
        }
        clean = {k: v for k, v in base_args.items() if v is not None and v != []}
        search_request = self.post_request_model(**clean)
        item_collection = await self._search_base(search_request, request=request)
        links = await ItemCollectionLinks(
            collection_id=collection_id, request=request
        ).get_links(extra_links=item_collection["links"])
        item_collection["links"] = links
        return item_collection

    async def get_item(self, item_id: str, collection_id: str, request: Optional[Request] = None, **kwargs) -> Item:
        """
        Retrieve a specific item from a collection.

        This method implements the `/collections/{collection_id}/items/{item_id}` endpoint,
        returning a single STAC Item.

        Args:
            item_id (str): The ID of the item to retrieve.
            collection_id (str): The ID of the collection containing the item.
            request (Request): The incoming HTTP request.

        Returns:
            Item: A STAC Item object.

        Raises:
            NotFoundError: If the specified item does not exist in the collection.
        """
        # If collection does not exist, NotFoundError will be raised
        if not item_id or not collection_id:
            raise NotFoundError("Item ID and Collection ID are required")

        # Validate collection exists
        await self.get_collection(collection_id, request=request)

        async with get_connection(request) as client:
            db = client[request.app.state.settings.mongodb_dbname]
            collection = db['items']
            query_filter = {
                "id": item_id,
                "collection": collection_id
            }
            item_data = await collection.find_one(query_filter)

            if not item_data:
                raise NotFoundError(
                    f"Item {item_id} in Collection {collection_id} does not exist."
                )

            # Remove MongoDB-specific fields
            item_data.pop("_id", None)

            return Item(**item_data)

    def _validate_bbox(self, bbox: Optional[List[NumType]]) -> Optional[List[NumType]]:
        """Validate bbox values."""
        if not bbox:
            return None

        if len(bbox) not in (4, 6):
            raise ValueError("BBOX must have 4 or 6 coordinates")

        # Validate coordinates
        if len(bbox) == 4:
            x_min, y_min, x_max, y_max = bbox
            if x_min > x_max or y_min > y_max:
                raise ValueError("Invalid BBOX coordinates")

        return bbox