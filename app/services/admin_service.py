"""
Admin service for common admin functionality
"""

from typing import Dict, Any, Optional
from datetime import datetime

from ..models.admin_action import AdminAction, ActionType
from ..models.user import User


class AdminService:
    """Service class for common admin operations"""

    @staticmethod
    async def log_admin_action(
        admin_id: str,
        action_type: ActionType,
        target_collection: str,
        target_id: str,
        changes: Dict[str, Any],
    ) -> None:
        """
        Centralized admin action logging

        Args:
            admin_id: ID of the admin performing the action
            action_type: Type of action being performed
            target_collection: Collection being modified
            target_id: ID of the target record
            changes: Dictionary of changes made
        """
        admin_action = AdminAction(
            admin_id=admin_id,
            action_type=action_type,
            target_collection=target_collection,
            target_id=target_id,
            changes=changes,
        )
        await admin_action.insert()

    @staticmethod
    def format_response(
        message: str,
        data: Optional[Any] = None,
        pagination: Optional[Dict[str, Any]] = None,
        changes: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Centralized response formatting

        Args:
            message: Response message
            data: Response data
            pagination: Pagination information
            changes: Changes made (for updates)
            **kwargs: Additional response fields

        Returns:
            Formatted response dictionary
        """
        response = {"message": message}

        if data is not None:
            response["data"] = data

        if pagination is not None:
            response["pagination"] = pagination

        if changes is not None:
            response["changes"] = changes

        response.update(kwargs)
        return response

    @staticmethod
    def validate_admin_access(user: User) -> bool:
        """
        Validate if user has admin access

        Args:
            user: User object to validate

        Returns:
            True if user has admin access, False otherwise
        """
        return user.role == UserRole.ADMIN and user.is_active

    @staticmethod
    def extract_image_urls(text: str) -> tuple[str, list[str]]:
        """
        Extract image URLs from text content

        Args:
            text: Text content that may contain image URLs

        Returns:
            Tuple of (clean_text, image_urls)
        """
        import re

        if not isinstance(text, str):
            return text, []

        # Pattern to match URLs
        url_pattern = r"https?://\S+"
        urls = re.findall(url_pattern, text)

        # Remove URLs from text
        clean_text = re.sub(url_pattern, "", text).strip()

        return clean_text, urls

    @staticmethod
    def normalize_enum(value: str, enum_cls) -> Any:
        """
        Normalize string value to enum member

        Args:
            value: String value to normalize
            enum_cls: Enum class to normalize to

        Returns:
            Enum member

        Raises:
            ValueError: If value cannot be normalized
        """
        for member in enum_cls:
            if value.lower() == member.value.lower():
                return member
        raise ValueError(
            f"Invalid {enum_cls.__name__}: {value}. "
            f"Allowed: {[m.value for m in enum_cls]}"
        )

    @staticmethod
    def build_query_filters(
        base_filters: Dict[str, Any],
        search: Optional[str] = None,
        search_fields: Optional[list[str]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Build MongoDB query filters with search functionality

        Args:
            base_filters: Base filters to start with
            search: Search term
            search_fields: Fields to search in
            **kwargs: Additional filters

        Returns:
            Complete query filters dictionary
        """
        filters = base_filters.copy()

        # Add search functionality
        if search and search_fields:
            search_conditions = []
            for field in search_fields:
                search_conditions.append({field: {"$regex": search, "$options": "i"}})
            filters["$or"] = search_conditions

        # Add additional filters
        for key, value in kwargs.items():
            if value is not None:
                filters[key] = value

        return filters

    @staticmethod
    def calculate_pagination(page: int, limit: int, total: int) -> Dict[str, Any]:
        """
        Calculate pagination information

        Args:
            page: Current page number
            limit: Items per page
            total: Total number of items

        Returns:
            Pagination information dictionary
        """
        total_pages = (total + limit - 1) // limit
        return {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
        }
