from typing import Optional
from pydantic import Field
from stac_pydantic.api import Search as BaseSearch

class WorldPopSearchRequest(BaseSearch):
    """Extended search request model with token support."""
    token: Optional[str] = Field(
        None,
        description="Pagination token"
    )

    class Config:
        """Pydantic config"""
        populate_by_name = True
        extra = "allow"
