"""WorldPop STAC API package."""
from typing import Dict, List, Optional

from wpstac.core import CoreCrudClient
from wpstac.config import Settings
from wpstac.version import __version__

class WorldPopSTAC:

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()
        self.client = CoreCrudClient()

    async def get_collections(self) -> List[Dict]:
        collections = await self.client.all_collections()
        return collections["collections"]

    async def get_collection(self, collection_id: str) -> Dict:
        return await self.client.get_collection(collection_id)

    async def get_item(self, collection_id: str, item_id: str) -> Dict:
        return await self.client.get_item(item_id, collection_id)

    async def search_items(
        self,
        collections: Optional[List[str]] = None,
        bbox: Optional[List[float]] = None,
        datetime: Optional[str] = None,
        limit: int = 10,
    ) -> Dict:
        search_request = {
            "collections": collections,
            "bbox": bbox,
            "datetime": datetime,
            "limit": limit
        }
        return await self.client.post_search(search_request)

stac = WorldPopSTAC()

__all__ = ["WorldPopSTAC", "stac", "Settings", "__version__"]