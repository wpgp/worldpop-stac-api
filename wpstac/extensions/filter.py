"""Get Queryables."""
import os
import sys
from typing import Any, Optional

from buildpg import render
from fastapi import Request
from fastapi.responses import JSONResponse
from stac_fastapi.extensions.core.filter.client import AsyncBaseFiltersClient

from stac_fastapi.types.errors import NotFoundError

from wpstac.db import get_connection


class FiltersClient(AsyncBaseFiltersClient):
    """STAC Filter Extension implementation."""

    async def get_queryables(
            self,
            request: Request = None,
            collection_id: Optional[str] = None,
            **kwargs: Any
    ) -> JSONResponse:
        """
        Get queryables schema for filtering.

        Args:
            request: FastAPI request
            collection_id: Optional collection ID to get specific queryables

        Returns:
            JSONResponse with queryables schema
        """
        async with get_connection(request) as client:
            db = client[request.app.state.settings.mongodb_dbname]
            collection = db["queryables"]

            # Базовая схема queryables
            base_schema = {
                "$schema": "https://json-schema.org/draft/2019-09/schema",
                "$id": str(request.url),
                "type": "object",
                "title": "STAC Queryables",
                "properties": {}
            }

            try:
                if collection_id:
                    query = {"collectionId": collection_id}
                    queryables = await collection.find_one(query)
                    if not queryables:
                        raise NotFoundError(f"No queryables found for collection {collection_id}")
                else:
                    # Get common queryables
                    queryables = await collection.find_one({"collectionId": "*"})

                if queryables:
                    queryables.pop("_id", None)
                    queryables.pop("collectionId", None)
                    base_schema["properties"] = queryables.get("properties", {})

                return JSONResponse(
                    content=base_schema,
                    headers={"Content-Type": "application/schema+json"}
                )
            except Exception as e:
                raise NotFoundError(f"Error retrieving queryables: {str(e)}")
