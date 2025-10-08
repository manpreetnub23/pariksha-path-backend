"""
Student service for student management operations
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from ..models.user import User
from ..models.enums import UserRole, ExamCategory
from ..models.user_analytics import UserAnalytics
from ..models.admin_action import ActionType
from .admin_service import AdminService


class StudentService:
    """Service class for student management operations"""

    @staticmethod
    async def get_students_with_filters(
        filters: Dict[str, Any],
        pagination: Dict[str, int],
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Get students with filtering and pagination

        Args:
            filters: Query filters
            pagination: Pagination parameters (page, limit)
            sort_by: Field to sort by
            sort_order: Sort order (asc/desc)

        Returns:
            Tuple of (students_list, pagination_info)
        """
        page = pagination.get("page", 1)
        limit = pagination.get("limit", 10)

        # Calculate pagination
        skip = (page - 1) * limit

        # Set sort order
        sort_direction = -1 if sort_order == "desc" else 1

        # Fetch users
        students = (
            await User.find(filters)
            .sort([(sort_by, sort_direction)])
            .skip(skip)
            .limit(limit)
            .to_list()
        )

        # Count total matching users for pagination info
        total_students = await User.find(filters).count()
        pagination_info = AdminService.calculate_pagination(page, limit, total_students)

        # Convert user objects to response format
        student_responses = []
        for student in students:
            student_responses.append(
                {
                    "id": str(student.id),
                    "name": student.name,
                    "email": student.email,
                    "phone": student.phone,
                    "role": student.role.value,
                    "is_active": student.is_active,
                    "is_verified": student.is_verified,
                    "is_email_verified": student.is_email_verified,
                    "preferred_exam_categories": [
                        cat.value for cat in student.preferred_exam_categories
                    ],
                    "enrolled_courses": student.enrolled_courses,
                    "created_at": student.created_at,
                    "last_login": student.last_login,
                }
            )

        return student_responses, pagination_info

    @staticmethod
    async def get_student_by_id(student_id: str) -> Optional[User]:
        """
        Get student by ID

        Args:
            student_id: Student ID

        Returns:
            User object if found, None otherwise
        """
        student = await User.get(student_id)
        if student and student.role == UserRole.STUDENT:
            return student
        return None
    

    @staticmethod
    async def update_student_data(
        student_id: str, update_data: Dict[str, Any]
    ) -> Tuple[Optional[User], Dict[str, Any]]:
        """
        Update student data

        Args:
            student_id: Student ID
            update_data: Data to update

        Returns:
            Tuple of (updated_student, changes_made)
        """
        student = await StudentService.get_student_by_id(student_id)
        if not student:
            return None, {}

        changes = {}

        # Update fields if provided
        for field, value in update_data.items():
            if value is not None:
                # Special validation for phone if provided
                if field == "phone" and value != student.phone:
                    # Check if phone already exists for another user
                    existing_phone = await User.find_one(
                        {"phone": value, "_id": {"$ne": student.id}}
                    )
                    if existing_phone:
                        raise ValueError("Phone number already exists")

                # Set the new value
                setattr(student, field, value)
                changes[field] = str(value)

        # Only update if there are changes
        if changes:
            student.update_timestamp()
            await student.save()

        return student, changes

    @staticmethod
    async def deactivate_student(student_id: str) -> bool:
        """
        Deactivate a student (soft delete)

        Args:
            student_id: Student ID

        Returns:
            True if deactivated, False if already inactive
        """
        student = await StudentService.get_student_by_id(student_id)
        if not student:
            return False

        # Check if student is already inactive
        if not student.is_active:
            return False

        # Soft delete by setting is_active=False
        student.is_active = False
        student.update_timestamp()
        await student.save()

        return True

    @staticmethod
    async def reset_student_password(student_id: str, new_password: str) -> bool:
        """
        Reset student password

        Args:
            student_id: Student ID
            new_password: New password

        Returns:
            True if password reset successfully
        """
        from ..auth import AuthService

        student = await StudentService.get_student_by_id(student_id)
        if not student:
            return False

        # Validate new password
        if not AuthService.validate_password(new_password):
            raise ValueError(
                "Password must be at least 8 characters long and contain "
                "uppercase, lowercase, number, and special character"
            )

        # Update password
        student.password_hash = AuthService.get_password_hash(new_password)
        student.update_timestamp()
        await student.save()

        return True

    @staticmethod
    async def get_student_analytics(
        student_id: str,
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Get student analytics data

        Args:
            student_id: Student ID

        Returns:
            Tuple of (student_info, analytics_data)
        """
        student = await StudentService.get_student_by_id(student_id)
        if not student:
            return {}, {}

        # Get analytics data from UserAnalytics collection
        analytics = await UserAnalytics.find_one({"user_id": student_id})

        if not analytics:
            # Create a new analytics record if none exists
            analytics = UserAnalytics(user_id=student_id)
            await analytics.insert()

        # Basic student info
        student_info = {
            "id": str(student.id),
            "name": student.name,
            "email": student.email,
            "preferred_exam_categories": [
                cat.value for cat in student.preferred_exam_categories
            ],
        }

        # Format analytics data
        analytics_data = {
            # Test performance
            "tests_taken": analytics.tests_taken,
            "tests_passed": analytics.tests_passed,
            "avg_accuracy": analytics.avg_accuracy,
            "avg_test_score": analytics.avg_test_score,
            "avg_percentile": analytics.avg_percentile,
            "best_percentile": analytics.best_percentile,
            # Subject performance
            "subject_performance": analytics.subject_performance,
            "strongest_subjects": analytics.strongest_subjects,
            "weakest_subjects": analytics.weakest_subjects,
            # Time and engagement
            "total_study_time_minutes": analytics.total_study_time_minutes,
            "study_habits": analytics.study_habits.dict(),
            "materials_accessed": analytics.materials_accessed,
            "materials_completed": analytics.materials_completed,
            # Detailed breakdowns
            "difficulty_performance": analytics.difficulty_performance,
            "exam_readiness": analytics.exam_readiness,
            # Last update time
            "last_updated": analytics.last_updated,
        }

        return student_info, analytics_data

    @staticmethod
    async def get_student_additional_info(student_id: str) -> Dict[str, Any]:
        """
        Get additional student information (purchases, test attempts, etc.)

        Args:
            student_id: Student ID

        Returns:
            Additional information dictionary
        """
        student = await StudentService.get_student_by_id(student_id)
        if not student:
            return {}

        return {
            "purchased_test_series": student.purchased_test_series,
            "purchased_materials": student.purchased_materials,
            "has_premium_access": student.has_premium_access,
            "completed_tests": len(student.completed_tests),
            "dashboard_settings": student.dashboard_settings,
        }
