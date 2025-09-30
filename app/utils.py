from typing import List, Dict, Any, Callable, Optional, TypeVar, Union, Tuple
from datetime import datetime, timezone
from fastapi import HTTPException, status
import asyncio
import hashlib

T = TypeVar("T")


async def paginate_query(
    model,
    query_filters: dict,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    page: int = 1,
    limit: int = 10,
    transform_func: Optional[Callable] = None,
) -> Tuple[List[Any], Dict[str, Any]]:
    """Generic pagination function for MongoDB queries

    Args:
        model: The Beanie document model to query
        query_filters: Dictionary of query filters
        sort_by: Field to sort by (default: created_at)
        sort_order: "asc" or "desc" (default: desc)
        page: Page number, 1-based (default: 1)
        limit: Items per page (default: 10)
        transform_func: Optional function to transform each item

    Returns:
        Tuple of (items_list, pagination_info)
    """
    # Calculate pagination
    skip = (page - 1) * limit

    # Set sort order
    sort_direction = 1 if sort_order == "asc" else -1

    # Fetch items
    items = (
        await model.find(query_filters)
        .sort([(sort_by, sort_direction)])
        .skip(skip)
        .limit(limit)
        .to_list()
    )

    # Count total matching items
    total_items = await model.find(query_filters).count()
    total_pages = (total_items + limit - 1) // limit if limit > 0 else 1

    # Transform items if needed
    result_list = []
    if items:
        if transform_func:
            # Handle both synchronous and asynchronous transform functions
            if asyncio.iscoroutinefunction(transform_func):
                tasks = [transform_func(item) for item in items]
                result_list = await asyncio.gather(*tasks)
            else:
                result_list = [transform_func(item) for item in items]
        else:
            result_list = items

    # Pagination info
    pagination_info = {
        "total": total_items,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
    }

    return result_list, pagination_info


async def get_or_404(model, id: str, detail: str = "Item not found"):
    """Get an item by ID or raise 404 exception

    Args:
        model: The Beanie document model to query
        id: The ID of the item to fetch
        detail: Custom error message for 404 response

    Returns:
        The found item

    Raises:
        HTTPException: 404 if item not found
    """
    item = await model.get(id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )
    return item


async def batch_get(model, ids: List[str]) -> Dict[str, Any]:
    """Get multiple items by ID in a single batch

    Args:
        model: The Beanie document model to query
        ids: List of item IDs to fetch

    Returns:
        Dictionary mapping ID strings to items
    """
    if not ids:
        return {}

    items = await model.find({"_id": {"$in": ids}}).to_list()
    return {str(item.id): item for item in items}


def format_response(
    message: str,
    data: Optional[Union[List[Any], Dict[str, Any]]] = None,
    pagination: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Dict[str, Any]:
    """Format a standardized API response

    Args:
        message: Response message
        data: Optional data to include
        pagination: Optional pagination information
        **kwargs: Additional fields to include in response

    Returns:
        Formatted response dictionary
    """
    response = {"message": message}

    if data is not None:
        # Use appropriate key based on data type
        if isinstance(data, list):
            # Use plural form based on the endpoint context
            response["items"] = data
        else:
            # Use singular form or the provided key
            response["data"] = data

    if pagination:
        response["pagination"] = pagination

    # Add any additional keyword arguments
    response.update(kwargs)

    return response


def safe_get_attr(obj: Any, attr: str, default: Any = None) -> Any:
    """Safely get an attribute from an object, return default if not found

    Args:
        obj: Object to get attribute from
        attr: Attribute name to get
        default: Default value if attribute not found

    Returns:
        Attribute value or default
    """
    return getattr(obj, attr, default) if hasattr(obj, attr) else default


def create_search_filter(
    search_text: Optional[str], fields: List[str]
) -> Optional[Dict]:
    """Create a MongoDB text search filter for multiple fields

    Args:
        search_text: Text to search for
        fields: List of fields to search in

    Returns:
        MongoDB filter dictionary or None if search_text is None
    """
    if not search_text:
        return None

    return {
        "$or": [{field: {"$regex": search_text, "$options": "i"}} for field in fields]
    }


def add_filter_if_not_none(filters: Dict, field: str, value: Any) -> Dict:
    """Add a filter condition if the value is not None

    Args:
        filters: Existing filter dictionary
        field: Field name to filter on
        value: Value to filter by (only added if not None)

    Returns:
        Updated filter dictionary
    """
    if value is not None:
        filters[field] = value
    return filters

def deterministic_receipt_hex12(course_id: str, user_id: str) -> str:
    raw = f"{course_id}:{user_id}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return digest[:12]  # 12 hex chars (0-9a-f)

# Usage