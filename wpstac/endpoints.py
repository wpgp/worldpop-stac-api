"""API endpoints for serving files and collections."""

import io
from typing import Optional, Dict, Any

import pycountry
from fastapi import APIRouter, HTTPException, Request, Path, Response
from motor.motor_asyncio import AsyncIOMotorCollection
from starlette.responses import FileResponse, StreamingResponse
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR
)

from wpstac.db import get_connection, handle_mongodb_errors

router = APIRouter(tags=["Files and Collections"])


async def get_mongo_collection(
        request: Request,
        collection_name: str
) -> AsyncIOMotorCollection:
    """Get MongoDB collection safely.

    Args:
        request: FastAPI request object
        collection_name: Name of MongoDB collection

    Returns:
        AsyncIOMotorCollection: MongoDB collection

    Raises:
        HTTPException: On invalid collection name or connection error
    """
    if not collection_name.isalnum():
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Invalid collection name"
        )

    async with get_connection(request) as client:
        try:
            db = client[request.app.state.settings.mongodb_dbname]
            return db[collection_name]
        except Exception as e:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {str(e)}"
            )


def get_country_name(country_code: str) -> str:
    """Get country name from country code.

    Args:
        country_code: ISO 3166-1 alpha-3 country code

    Returns:
        str: Country name or original code if not found
    """
    try:
        country = pycountry.countries.get(alpha_3=country_code)
        return country.name if country else country_code
    except (LookupError, AttributeError):
        return country_code


@router.get(
    "/{sub_path:path}/{filename}",
    summary="Serve file from MongoDB",
    response_description="File content or metadata"
)
async def serve_file(
        request: Request,
        sub_path: str = Path(..., description="Collection path"),
        filename: str = Path(..., description="File identifier")
):
    """Serve file from MongoDB GridFS or collection.

    Args:
        request: FastAPI request
        sub_path: Path to collection
        filename: File identifier

    Returns:
        Response with file content or metadata
    """
    async with handle_mongodb_errors():
        collection = await get_mongo_collection(request, sub_path)
        result = await collection.find_one({'_id': filename})

        if not result:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail="File not found"
            )

        # Handle binary files
        if collection.name == 'files':
            if 'image' in result:
                return StreamingResponse(
                    io.BytesIO(result['image']),
                    media_type="image/png"
                )
            if 'pdf' in result:
                return StreamingResponse(
                    io.BytesIO(result['pdf']),
                    media_type="application/pdf"
                )

        # Return metadata without internal ID
        result.pop('_id', None)
        return result


@router.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Serve favicon."""
    return FileResponse("favicon.ico")


@router.get(
    "/{sub_path:path}",
    summary="Get collection by ID",
    response_description="Collection metadata"
)
async def get_by_collection_id(
        request: Request,
        sub_path: str = Path(..., description="Collection path")
) -> Dict[str, Any]:
    """Get collection metadata with country-specific customization.

    Args:
        request: FastAPI request
        sub_path: Collection path with optional country code

    Returns:
        Dict[str, Any]: Collection metadata
    """
    parts = sub_path.split('-')
    collection_name = parts[0]
    country_code: Optional[str] = None

    # Parse path and build template ID
    if len(parts) > 1:
        country_code = parts[1]
        template_id = (
            f"{collection_name}-CODE-{'-'.join(parts[2:])}"
            if len(parts) > 2
            else f"{collection_name}-CODE"
        )
    else:
        template_id = collection_name

    async with handle_mongodb_errors():
        # Get template
        catalogs_collection = await get_mongo_collection(request, 'catalogs')
        template = await catalogs_collection.find_one({'id': template_id})
        if not template:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail="Template not found"
            )

        # Prepare result
        result = template.copy()

        # Replace placeholders with country code
        if country_code:
            result['id'] = result['id'].replace('CODE', country_code)

            # Get country-specific data
            collections = await get_mongo_collection(request, 'collections')
            country_data = await collections.find_one({'id': country_code})

            if country_data:
                result['extent']['spatial']['bbox'] = country_data['extent']['spatial']['bbox']
                result['extent']['temporal']['interval'] = country_data['extent']['temporal']['interval']

            # Update links
            for link in result['links']:
                link['href'] = link['href'].replace('CODE', country_code)
                if 'title' in link and 'ITEM' in link['title']:
                    link['title'] = link['title'].replace('ITEM', country_code)
                    link['href'] = link['href'].replace('ITEM_', f'{country_code.lower()}_')

        result.pop('_id', None)
        return result