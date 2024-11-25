import os
import sys
from typing import Dict

from fastapi.openapi.utils import get_openapi
from fastapi.responses import ORJSONResponse
from stac_pydantic.version import STAC_VERSION


from stac_fastapi.api.app import StacApi
from stac_fastapi.api.models import create_get_request_model, create_post_request_model, create_request_model, \
    ItemCollectionUri
from stac_fastapi.api.errors import add_exception_handlers, DEFAULT_STATUS_CODES
from stac_fastapi.extensions.core import (
    FieldsExtension,
    FilterExtension,
    SortExtension,
    TokenPaginationExtension,
)
from stac_fastapi.types.extension import ApiExtension

from wpstac.config import Settings
from wpstac.version import __version__
from wpstac.core import CoreCrudClient
from wpstac.db import close_db_connection, connect_to_db
from wpstac.endpoints import router
from wpstac.extensions.query import QueryExtension
from wpstac.extensions.filter import FiltersClient

wp_stac_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(wp_stac_root)

settings = Settings()

extensions_map: Dict[str, ApiExtension] = {
    "query": QueryExtension(),
    "sort": SortExtension(),
    "fields": FieldsExtension(),
    "pagination": TokenPaginationExtension(),
    # "filter": FilterExtension(client=FiltersClient()),
}

if enabled_extensions := os.getenv("ENABLED_EXTENSIONS"):
    extensions = [
        extensions_map[extension_name]
        for extension_name in enabled_extensions.split(",")
        if extension_name in extensions_map
    ]
else:
    extensions = list(extensions_map.values())

post_request_model = create_post_request_model(extensions)
get_request_model = create_get_request_model(extensions)
items_get_request_model = create_request_model(
    "ItemCollectionUriWithToken",
    base_model=ItemCollectionUri,
    mixins=[TokenPaginationExtension().GET],
)

api = StacApi(
    settings=settings,
    extensions=extensions,
    client=CoreCrudClient(post_request_model=post_request_model),
    response_class=ORJSONResponse,
    search_get_request_model=get_request_model,
    search_post_request_model=post_request_model,
    items_get_request_model=items_get_request_model,
    stac_version=STAC_VERSION,
    api_version=__version__,
)


def custom_openapi():
    if api.app.openapi_schema:
        return api.app.openapi_schema

    openapi_schema = get_openapi(
        title=settings.stac_fastapi_title,
        version=settings.stac_fastapi_version,
        description=settings.stac_fastapi_description,
        routes=api.app.routes,
        tags=settings.stac_fastapi_openapi_tags
    )

    if "tags" not in openapi_schema:
        openapi_schema["tags"] = []

    openapi_schema["tags"].insert(0, {
        "name": "STAC",
        "description": "Core STAC API endpoints"
    })

    for path in openapi_schema["paths"].values():
        for method in path.values():
            if "tags" not in method:
                method["tags"] = ["STAC"]

    api.app.openapi_schema = openapi_schema
    return api.app.openapi_schema


api.app.openapi = custom_openapi

app = api.app

app.include_router(router)

add_exception_handlers(app, status_codes=DEFAULT_STATUS_CODES)

@app.on_event("startup")
async def startup_event():
    await connect_to_db(app)

@app.on_event("shutdown")
async def shutdown_event():
    await close_db_connection(app)

@app.get("/_mgmt/ping", tags=["Health Check"])
async def ping():
    return {"message": "PONG"}


def run():
    try:
        import uvicorn
        root_path = os.getenv("UVICORN_ROOT_PATH", "").rstrip("/")

        uvicorn.run(
            "wpstac.app:app",
            host=settings.app_host,
            port=settings.app_port,
            log_level=settings.log_level.lower(),
            reload=settings.reload,
            root_path=root_path
        )
    except ImportError:
        raise RuntimeError("Uvicorn must be installed in order to use command")


# AWS Lambda handler
def create_handler(app):
    try:
        from mangum import Mangum
        return Mangum(app)
    except ImportError:
        return None


if __name__ == "__main__":
    run()

handler = create_handler(app)