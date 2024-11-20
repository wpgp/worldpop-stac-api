"""Search functionality for STAC API."""

import re
from abc import ABC
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from urllib.parse import unquote_plus

import attr
import orjson
from bson import ObjectId
from fastapi import HTTPException, Request
from pydantic import ValidationError
from pygeofilter.backends.cql2_json import to_cql2
from pygeofilter.parsers.cql2_text import parse as parse_cql2_text
from pypgstac.hydration import hydrate
from stac_fastapi.types.core import AsyncBaseCoreClient
from stac_fastapi.types.search import NumType
from stac_fastapi.types.stac import Item, ItemCollection
from stac_pydantic.api import Search
from starlette.datastructures import URL

from wpstac.config import Settings
from wpstac.db import get_connection
from wpstac.utils import ItemLinks, filter_fields, PagingLinks


@attr.s
class SearchMixin(AsyncBaseCoreClient, ABC):
    """Search operations mixin."""

    async def _add_item_links(
            self,
            feature: Item,
            collection_id: Optional[str] = None,
            item_id: Optional[str] = None,
            request: Optional[Request] = None,
            fields: Optional[Any] = None
    ) -> None:
        """Add ItemLinks to the Item.

        Args:
            feature: STAC Item to add links to
            collection_id: Optional collection ID
            item_id: Optional item ID
            request: FastAPI request object
            fields: Fields filtering configuration
        """
        collection_id = feature.get("collection") or collection_id
        item_id = feature.get("id") or item_id

        if (
                not fields or
                fields.exclude is None or
                "links" not in fields.exclude
        ) and all([collection_id, item_id]):
            feature["links"] = await ItemLinks(
                collection_id=collection_id,
                item_id=item_id,
                request=request,
            ).get_links(extra_links=feature.get("links"))

    async def _search_base(self, search_request: Search, request: Request) -> ItemCollection:
        """
        Perform base search operation across the STAC catalog.

        Args:
            search_request: Search parameters from STAC API
            request: FastAPI request object

        Returns:
            ItemCollection containing matching items with pagination
        """
        settings: Settings = request.app.state.settings

        # Build base query filter
        filter_dict = {}

        # Add collection filter
        if search_request.collections:
            filter_dict["collection"] = {"$in": search_request.collections}

        # Add IDs filter
        if search_request.ids:
            filter_dict["id"] = {"$in": search_request.ids}

        # Add spatial filter
        if search_request.bbox:
            filter_dict["bbox"] = {
                "$geoWithin": {
                    "$box": [
                        [search_request.bbox[0], search_request.bbox[1]],
                        [search_request.bbox[2], search_request.bbox[3]]
                    ]
                }
            }

        # Add temporal filter
        if search_request.datetime:
            filter_dict["datetime"] = {"$gte": search_request.datetime}

        # Handle pagination token
        if search_request.token:
            try:
                direction, token_id = search_request.token.split(':')
                if direction == 'next':
                    filter_dict["_id"] = {"$gt": ObjectId(token_id)}
                elif direction == 'prev':
                    filter_dict["_id"] = {"$lt": ObjectId(token_id)}
            except (ValueError, IndexError):
                raise HTTPException(status_code=400, detail="Invalid pagination token")

        async with get_connection(request) as client:
            db = client[request.app.state.settings.mongodb_dbname]
            collection = db['items']

            # Get total count for numberMatched
            total_count = await collection.count_documents(filter_dict)

            # Execute search query
            cursor = (
                collection.find(filter_dict)
                .sort("_id", 1)  # Consistent ordering for pagination
                .limit(search_request.limit + 1)  # Get one extra for next page token
            )

            # Convert cursor to list
            items = []
            async for item in cursor:
                item["_id"] = str(item["_id"])
                items.append(item)

            # Handle pagination tokens
            next_token = None
            if len(items) > search_request.limit:
                next_token = f"next:{items[search_request.limit - 1]['_id']}"
                items = items[:search_request.limit]

            prev_token = None
            if items and search_request.token:
                # Get previous page starting point
                prev_cursor = (
                    collection.find({"_id": {"$lt": ObjectId(items[0]["_id"])}})
                    .sort("_id", -1)
                    .limit(1)
                )
                prev_item = await prev_cursor.fetch_next
                if prev_item:
                    prev_token = f"prev:{str(prev_item['_id'])}"

            # Create response collection
            collection = ItemCollection(
                type="FeatureCollection",
                features=items,
                links=[]
            )

            # Handle field filtering
            cleaned_features: List[Item] = []
            if settings.use_api_hydrate:
                # Get base item for hydration
                async def _get_base_item(collection_id: str) -> Dict[str, Any]:
                    return await self._get_base_item(collection_id, request=request)

                # Set up item cache
                base_item_cache = settings.base_item_cache(
                    fetch_base_item=_get_base_item,
                    request=request
                )

                # Process each feature
                for feature in collection.get("features") or []:
                    base_item = await base_item_cache.get(feature.get("collection"))
                    feature = hydrate(base_item, feature)

                    # Filter fields if requested
                    if search_request.fields:
                        feature = filter_fields(
                            feature,
                            search_request.fields.include,
                            search_request.fields.exclude
                        )

                    # Add required links
                    await self._add_item_links(
                        feature,
                        collection_id=feature.get("collection"),
                        item_id=feature.get("id"),
                        request=request,
                        fields=search_request.fields
                    )
                    cleaned_features.append(feature)
            else:
                cleaned_features = collection.get("features") or []

            # Update collection with processed features
            collection["features"] = cleaned_features

            # Add pagination links
            collection["links"] = await PagingLinks(
                request=request,
                next=next_token,
                prev=prev_token
            ).get_links()

            # Add count metadata
            collection["numberMatched"] = total_count
            collection["numberReturned"] = len(cleaned_features)

            return collection

    async def post_search(self, search_request: Search, request: Optional[Request] = None, **kwargs) -> ItemCollection:
        """
         Perform a search using POST method.

         This method implements the POST `/search` endpoint, allowing for more complex
         queries than the GET method.

         Args:
             search_request (Search): The search parameters.
             request (Request): The incoming HTTP request.

         Returns:
             ItemCollection: A STAC ItemCollection containing the search results.
         """

        # item_collection = await self._search_base(search_request, request=request)
        # response_features = item_collection["features"]
        # response_links = item_collection["links"]
        # for link in response_links:
        #     if isinstance(link["href"], URL):
        #         link["href"] = str(link["href"])
        #
        # response_data = {
        #     "type": "FeatureCollection",
        #     "features": response_features,
        #     "links": response_links,
        #     "numberMatched": len(response_features),
        #     "numberReturned": len(response_features),
        # }
        # return ItemCollection(**response_data)
        return await self._search_base(search_request, request=request)

    async def get_search(
            self,
            request: Optional[Request] = None,
            collections: Optional[List[str]] = None,
            ids: Optional[List[str]] = None,
            bbox: Optional[List[NumType]] = None,
            datetime: Optional[Union[str, datetime]] = None,
            limit: Optional[int] = None,
            query: Optional[str] = None,
            token: Optional[str] = None,
            fields: Optional[List[str]] = None,
            sortby: Optional[str] = None,
            filter: Optional[str] = None,
            filter_lang: Optional[str] = None,
            intersects: Optional[str] = None,
            **kwargs,
    ) -> ItemCollection:
        """
        Perform a search using GET method.

        This method implements the GET `/search` endpoint, allowing for item searches
        with various filter parameters.

        Args:
            request (Request): The incoming HTTP request.
            collections (Optional[List[str]]): List of collection IDs to search in.
            ids (Optional[List[str]]): List of item IDs to return.
            bbox (Optional[List[NumType]]): Bounding box for spatial filtering.
            datetime (Optional[Union[str, datetime]]): Temporal filter.
            limit (Optional[int]): Maximum number of items to return.
            query (Optional[str]): CQL query for filtering items.
            token (Optional[str]): Pagination token.
            fields (Optional[List[str]]): Fields to include or exclude in the response.
            sortby (Optional[str]): Sort order for the results.
            filter (Optional[str]): CQL filter for the search.
            filter_lang (Optional[str]): Language of the filter (e.g., "cql2-text").
            intersects (Optional[str]): GeoJSON geometry to search within.

        Returns:
            ItemCollection: A STAC ItemCollection containing the search results.

        Raises:
            HTTPException: If invalid parameters are provided.
        """
        if limit is not None:
            limit = self._validate_page_size(limit)

        base_args = {
            "collections": collections,
            "ids": ids,
            "bbox": bbox,
            "limit": limit,
            "token": token,
        }

        if datetime:
            base_args["datetime"] = datetime

        if query:
            try:
                base_args["query"] = orjson.loads(unquote_plus(query))
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid query parameter format"
                )

        if filter:
            try:
                if filter_lang == "cql2-text":
                    ast = parse_cql2_text(filter)
                    base_args["filter"] = orjson.loads(to_cql2(ast))
                    base_args["filter-lang"] = "cql2-json"
                else:
                    base_args["filter"] = filter
                    base_args["filter-lang"] = filter_lang
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid filter format: {str(e)}"
                )

        if intersects:
            try:
                base_args["intersects"] = orjson.loads(unquote_plus(intersects))
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid intersects parameter format"
                )

        if sortby:
            sort_param = []
            for sort in sortby:
                if match := re.match(r"^([+-]?)(.*)$", sort):
                    sort_param.append({
                        "field": match.group(2).strip(),
                        "direction": "desc" if match.group(1) == "-" else "asc"
                    })
            if sort_param:
                base_args["sortby"] = sort_param

        if fields:
            includes = set()
            excludes = set()
            for field in fields:
                if field.startswith("-"):
                    excludes.add(field[1:])
                elif field.startswith("+"):
                    includes.add(field[1:])
                else:
                    includes.add(field)
            base_args["fields"] = {"include": includes, "exclude": excludes}

        clean = {k: v for k, v in base_args.items() if v is not None and v != []}

        try:

            search_request = self.post_request_model(**clean)
        except ValidationError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid search parameters: {str(e)}"
            )

        return await self.post_search(search_request, request=request)
