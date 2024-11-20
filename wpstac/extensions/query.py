"""Query Extension implementation for WorldPop STAC API.

This module provides custom query functionality for the STAC API,
allowing filtering of items based on their properties.
"""

import operator
from enum import auto
from types import DynamicClassAttribute
from typing import Any, Callable, Dict, Optional, Type

from pydantic import BaseModel, Field
from stac_fastapi.extensions.core.query import QueryExtension as QueryExtensionBase
from stac_pydantic.utils import AutoValueEnum


class Operator(str, AutoValueEnum):
    """Defines the set of operators supported by the API.

    Attributes:
        eq: Equal to
        ne: Not equal to
        lt: Less than
        lte: Less than or equal to
        gt: Greater than
        gte: Greater than or equal to

    Future operators (not yet implemented):
        startsWith: String starts with
        endsWith: String ends with
        contains: String contains
        in: Value in list
    """

    eq = auto()  # Equal
    ne = auto()  # Not equal
    lt = auto()  # Less than
    lte = auto() # Less than or equal
    gt = auto()  # Greater than
    gte = auto() # Greater than or equal
    in_ = auto() # In list
    contains = auto() # String contains
    startsWith = auto() # String starts with
    endsWith = auto() # String ends with

    @DynamicClassAttribute
    def operator(self) -> Callable[[Any, Any], bool]:
        """Get operator function."""
        op_map = {
            'eq': operator.eq,
            'ne': operator.ne,
            'lt': operator.lt,
            'lte': operator.le,
            'gt': operator.gt,
            'gte': operator.ge,
            'in_': lambda x, y: x in y,
            'contains': lambda x, y: y in x if isinstance(x, str) else False,
            'startsWith': lambda x, y: x.startswith(y) if isinstance(x, str) else False,
            'endsWith': lambda x, y: x.endswith(y) if isinstance(x, str) else False,
        }
        return op_map[self._value_]


class QueryExtensionPostRequest(BaseModel):
    """Query Extension POST request model."""

    query: Optional[Dict[str, Dict[Operator, Any]]] = Field(
        None,
        description="Query parameters for filtering items",
        examples=[{
            "query": {
                "datetime": {"gte": "2020-01-01T00:00:00Z"},
                "gsd": {"lte": 10},
                "eo:cloud_cover": {"lt": 50},
                "platform": {"in_": ["sentinel-2a", "sentinel-2b"]}
            }
        }]
    )


class QueryExtension(QueryExtensionBase):
    """WorldPop STAC Query Extension."""

    POST = QueryExtensionPostRequest

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize Query Extension."""
        super().__init__(*args, **kwargs)
        self.conformance_classes = [
            "https://api.stacspec.org/v1.0.0/item-search#query",
            "https://api.stacspec.org/v1.0.0/item-search#filter",
        ]