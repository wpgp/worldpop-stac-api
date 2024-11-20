import os
from typing import List, Type, Dict, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Extra, validator
from stac_fastapi.types.config import ApiSettings

from wpstac.utils.cache import (
    DefaultBaseItemCache, BaseItemCache,
)
load_dotenv()

DEFAULT_INVALID_ID_CHARS = [
    ":",
    "/",
    "?",
    "#",
    "[",
    "]",
    "@",
    "!",
    "$",
    "&",
    "'",
    "(",
    ")",
    "*",
    "+",
    ",",
    ";",
    "=",
]


class ServerSettings(BaseModel, extra=Extra.allow):
    """Server runtime parameters."""

    search_path: str = "wpstac,public"
    application_name: str = "wpstac"


class Settings(ApiSettings):
    """Settings for the WorldPop STAC API.

    This class contains all configuration parameters for the API, including:
    - Server settings (host, port, etc.)
    - MongoDB connection settings
    - Redis settings (if used)
    - Logging configuration
    - API metadata
    - Security settings

    Environment variables can be used to override any of these settings.
    """

    app_host: str = os.getenv("APP_HOST", "127.0.0.1")
    app_port: int = int(os.getenv("APP_PORT", 8000))
    reload: bool = os.getenv("RELOAD", "false").lower() == "true"

    """MongoDB-specific API settings."""
    mongodb_host: str = os.getenv("MONGODB_HOST", "localhost")
    mongodb_port: int = int(os.getenv("MONGODB_PORT", "27017"))
    mongodb_dbname: str = os.getenv("MONGODB_DB", "stac_worldpop_db")
    mongodb_username: Optional[str] = os.getenv("MONGODB_USERNAME")
    mongodb_password: Optional[str] = os.getenv("MONGODB_PASSWORD")

    use_api_hydrate: bool = True
    base_item_cache: Type[BaseItemCache] = DefaultBaseItemCache
    invalid_id_chars: List[str] = DEFAULT_INVALID_ID_CHARS

    testing: bool = False

    @property
    def mongodb_connection_string(self) -> str:
        """Create MongoDB connection string with optional authentication."""
        if self.mongodb_username and self.mongodb_password:
            return f"mongodb://{self.mongodb_username}:{self.mongodb_password}@{self.mongodb_host}:{self.mongodb_port}/{self.mongodb_dbname}"
        return f"mongodb://{self.mongodb_host}:{self.mongodb_port}/{self.mongodb_dbname}"

    # Redis settings
    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("REDIS_PORT", 6379))
    redis_db: int = int(os.getenv("REDIS_DB", 0))

    # Logging settings
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_file: str = os.getenv("LOG_FILE", "app.log")

    # API metadata
    stac_fastapi_title: str = "WorldPop STAC API"
    stac_fastapi_description: str = (
        "Welcome to the WorldPop STAC API, a specialized platform for accessing "
        "and analyzing global population distribution and covariate data. This API "
        "utilizes the SpatioTemporal Asset Catalog (STAC) specification to provide "
        "standardized access to a range of geospatial datasets related to human "
        "population and environmental factors."
    )
    stac_fastapi_version: str = "1.0.0"
    stac_fastapi_openapi_tags: List[Dict[str, str]] = [
        {"name": "Core", "description": "Core STAC API endpoints"},
        {"name": "Collections", "description": "Endpoints for managing collections"},
        {"name": "Items", "description": "Endpoints for managing items"},
        {"name": "Search", "description": "Search endpoints"},
    ]

    # Security settings
    enable_response_models: bool = True
    docs_url: str = "/api.html"
    openapi_url: str = "/api"

    # CORS settings
    cors_allow_origins: List[str] = ["*"]
    cors_allow_methods: List[str] = ["GET", "POST", "OPTIONS"]
    cors_allow_headers: List[str] = ["*"]
    cors_expose_headers: List[str] = []
    cors_max_age: int = 600

    # Pagination settings
    default_limit: int = 10
    max_limit: int = 10000

    # Cache settings
    cache_ttl: int = 3600
    use_cache: bool = True

    # Search settings
    search_request_limit: int = int(os.getenv("SEARCH_REQUEST_LIMIT", "1000"))

    # Filter settings
    filter_lang_default: str = "cql2-text"

    # MongoDB index settings
    create_indexes: bool = True
    index_creation_timeout: int = 60

    # Rate limiting
    rate_limit: Optional[int] = None
    rate_limit_period: int = 60

    @validator("mongodb_port", "app_port")
    def check_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        return v

    @validator("mongodb_host")
    def check_mongodb_host(cls, v):
        if not v:
            raise ValueError("MongoDB host cannot be empty")
        return v

    @validator("mongodb_dbname")
    def check_mongodb_dbname(cls, v):
        if not v:
            raise ValueError("MongoDB database name cannot be empty")
        return v

    @validator("log_level")
    def check_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()

    @validator("search_request_limit")
    def validate_search_limit(cls, v):
        if not 1 <= v <= 10000:
            raise ValueError("Search limit must be between 1 and 10000")
        return v
