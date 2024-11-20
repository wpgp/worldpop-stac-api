"""Utility methods for STAC API field filtering."""
from typing import Any, Dict, Optional, Set, Union, TypeVar, cast

from stac_fastapi.types.stac import Item

T = TypeVar('T', bound=Union[Item, Dict[str, Any]])

def filter_fields(
    item: T,
    include: Optional[Set[str]] = None,
    exclude: Optional[Set[str]] = None,
) -> T:
    """Filter STAC Item fields based on include/exclude sets.

    Args:
        item: STAC Item or dict to filter
        include: Set of field paths to include
        exclude: Set of field paths to exclude

    Returns:
        Filtered copy of the input item

    Examples:
        >>> item = {"id": "1", "properties": {"datetime": "2021-01-01", "extra": "value"}}
        >>> filter_fields(item, include={"id", "properties.datetime"})
        {"id": "1", "properties": {"datetime": "2021-01-01"}}
    """
    if not include and not exclude:
        return item

    def include_fields(
        source: Dict[str, Any],
        fields: Optional[Set[str]]
    ) -> Dict[str, Any]:
        """Build a shallow copy with only included fields."""
        if not fields:
            return source

        clean_item: Dict[str, Any] = {}
        for key_path in fields:
            key_parts = key_path.split(".")
            key_root = key_parts[0]

            if key_root not in source:
                continue

            if isinstance(source[key_root], dict) and len(key_parts) > 1:
                # Handle nested dictionary
                nested_value = include_fields(
                    source[key_root],
                    fields={".".join(key_parts[1:])}
                )

                if isinstance(clean_item.get(key_root), dict):
                    dict_deep_update(clean_item[key_root], nested_value)
                else:
                    clean_item[key_root] = nested_value
            else:
                clean_item[key_root] = source[key_root]

        return clean_item

    def exclude_fields(
        source: Dict[str, Any],
        fields: Optional[Set[str]]
    ) -> None:
        """Remove excluded fields from dictionary in-place."""
        if not fields:
            return

        for key_path in fields:
            key_parts = key_path.split(".")
            key_root = key_parts[0]

            if key_root not in source:
                continue

            if isinstance(source[key_root], dict) and len(key_parts) > 1:
                # Handle nested dictionary
                exclude_fields(
                    source[key_root],
                    fields={".".join(key_parts[1:])}
                )
                if not source[key_root]:  # Remove empty dict
                    del source[key_root]
            else:
                source.pop(key_root, None)

    # Convert to dict if needed
    item_dict = dict(item)

    # Apply includes
    clean_item = include_fields(item_dict, include)

    # Handle empty result
    if not clean_item:
        result = {
            "id": item_dict.get("id"),
            "collection": item_dict.get("collection")
        }
        return cast(T, Item(**result) if isinstance(item, Item) else result)

    # Apply excludes
    exclude_fields(clean_item, exclude)

    # Return same type as input
    return cast(T, Item(**clean_item) if isinstance(item, Item) else clean_item)


def dict_deep_update(
    merge_to: Dict[str, Any],
    merge_from: Dict[str, Any],
    inplace: bool = True
) -> Dict[str, Any]:
    """Perform a deep update of dictionaries.

    Args:
        merge_to: Base dictionary to update
        merge_from: Dictionary with values to merge
        inplace: Whether to modify merge_to in-place

    Returns:
        Updated dictionary
    """
    if not inplace:
        merge_to = merge_to.copy()

    for key, value in merge_from.items():
        if (
            key in merge_to
            and isinstance(merge_to[key], dict)
            and isinstance(value, dict)
        ):
            dict_deep_update(merge_to[key], value)
        else:
            merge_to[key] = value

    return merge_to

def validate_field_path(field_path: str) -> bool:
    """Validate field path format."""
    parts = field_path.split('.')
    return all(part.isalnum() or part == '_' for part in parts)