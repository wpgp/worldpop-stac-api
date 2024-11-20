"""Cache implementations for STAC items."""

import abc
import time
from typing import Any, Callable, Coroutine, Dict

from starlette.requests import Request


class BaseItemCache(abc.ABC):
    """Base cache interface for STAC items.

    This abstract class defines the interface for caching base items for collections.
    Implementations should provide caching mechanisms to avoid repeated database queries.
    """

    def __init__(
        self,
        fetch_base_item: Callable[[str], Coroutine[Any, Any, Dict[str, Any]]],
        request: Request,
    ):
        """Initialize the base item cache.

        Args:
            fetch_base_item: Async function to fetch base item for a collection
            request: FastAPI request object for access to app state
        """
        self._fetch_base_item = fetch_base_item
        self._request = request

    @abc.abstractmethod
    async def get(self, collection_id: str) -> Dict[str, Any]:
        """Get base item for collection, fetching and caching if needed.

        Args:
            collection_id: ID of the collection

        Returns:
            Dict containing the base item
        """
        raise NotImplementedError


class DefaultBaseItemCache(BaseItemCache):
    """In-memory dictionary cache implementation."""

    def __init__(
        self,
        fetch_base_item: Callable[[str], Coroutine[Any, Any, Dict[str, Any]]],
        request: Request,
        max_items: int = 1000,
        cache_ttl: int = 3600,
    ):
        """Initialize the cache.

        Args:
            fetch_base_item: Async function to fetch base items
            request: FastAPI request object
            max_items: Maximum number of items to cache
        """
        self._cache_ttl = cache_ttl
        self._timestamps: Dict[str, float] = {}
        self._base_items: Dict[str, Dict[str, Any]] = {}
        self._max_items = max_items
        super().__init__(fetch_base_item, request)

    async def get(self, collection_id: str) -> Dict[str, Any]:
        if not collection_id:
            raise ValueError("Collection ID cannot be empty")

        current_time = time.time()
        if (
            collection_id in self._base_items
            and current_time - self._timestamps.get(collection_id, 0) < self._cache_ttl
        ):
            return self._base_items[collection_id]

        if len(self._base_items) >= self._max_items:
            items = list(self._base_items.items())
            self._base_items = dict(items[len(items)//2:])
            self._timestamps = {k: v for k, v in self._timestamps.items() if k in self._base_items}

        self._base_items[collection_id] = await self._fetch_base_item(collection_id)
        self._timestamps[collection_id] = current_time

        return self._base_items[collection_id]

    def clear(self) -> None:
        self._base_items.clear()
        self._timestamps.clear()