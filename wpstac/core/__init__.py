"""Core STAC API implementation."""

from wpstac.core.base import BaseClient
from wpstac.core.collections import CollectionsMixin
from wpstac.core.items import ItemsMixin
from wpstac.core.search import SearchMixin
from wpstac.models.search import WorldPopSearchRequest


class CoreCrudClient(BaseClient, CollectionsMixin, ItemsMixin, SearchMixin):
    """Complete STAC API implementation for WorldPop.

    This class combines base STAC API functionality with WorldPop-specific
    implementations for collections, items and search operations.

    Attributes:
        base_conformance_classes (List[str]): Base STAC API conformance classes
        extensions (List[ApiExtension]): Enabled API extensions
        post_request_model: Model for POST request validation
    """
    post_request_model = WorldPopSearchRequest

    def __init__(self, *args, **kwargs):
        """Initialize CoreCrudClient.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        super().__init__(*args, **kwargs)