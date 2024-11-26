"""Core STAC API implementation."""
from typing import Any, Dict, List, Optional, Type

import attr
from stac_fastapi.types.core import AsyncBaseCoreClient
from stac_fastapi.types.extension import ApiExtension
from stac_pydantic.api import Search

from wpstac.core.base import BaseClient
from wpstac.core.collections import CollectionsMixin
from wpstac.core.items import ItemsMixin
from wpstac.core.search import SearchMixin


@attr.s
class CoreCrudClient(BaseClient, CollectionsMixin, ItemsMixin, SearchMixin):
    """Complete STAC API implementation for WorldPop.

    This class combines base STAC API functionality with WorldPop-specific
    implementations for collections, items and search operations.

    Attributes:
        base_conformance_classes (List[str]): Base STAC API conformance classes
        extensions (List[ApiExtension]): Enabled API extensions
        post_request_model: Model for POST request validation
    """

    settings = attr.ib(default=None)
    api_version = attr.ib(default="1.0.0")
    post_request_model = attr.ib(default=None)
    base_conformance_classes: List[str] = attr.ib(factory=list)
    extensions: List[ApiExtension] = attr.ib(factory=list)

    def __attrs_post_init__(self):
        """Post initialization hook.

        This ensures all mixins are properly initialized and have access
        to shared attributes.
        """

        super().__attrs_post_init__() if hasattr(super(), '__attrs_post_init__') else None

        for base in [CollectionsMixin, ItemsMixin, SearchMixin]:
            if hasattr(base, '__attrs_post_init__'):
                base.__attrs_post_init__(self)

    @classmethod
    def create(
        cls,
        post_request_model: Type[Search],
        settings: Optional[Any] = None,
        extensions: Optional[List[ApiExtension]] = None,
        **kwargs: Dict[str, Any]
    ) -> "CoreCrudClient":
        """Factory method to create a properly configured instance.

        Args:
            post_request_model: Search request model with extensions
            settings: API settings
            extensions: List of enabled API extensions
            **kwargs: Additional keyword arguments

        Returns:
            Configured CoreCrudClient instance
        """
        return cls(
            post_request_model=post_request_model,
            settings=settings,
            extensions=extensions or [],
            **kwargs
        )
