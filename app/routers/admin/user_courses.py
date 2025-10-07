"""
User course enrollment management endpoints for admin
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, Dict, Any
from datetime import datetime

from ...models.user import User
from ...models.course import Course
from ...models.course_enrollment import CourseEnrollment
from ...models.enums import UserRole, ExamCategory
from ...dependencies import admin_required
from ...services.admin_service import AdminService
from ...services.course_service import CourseService
from .schemas import StandardResponse
from ...models.admin_action import ActionType

router = APIRouter(prefix="/user-courses", tags=["Admin - User Courses"])


@router.get(
    "/enrollments",
    response_model=Dict[str, Any],
    summary="List all course enrollments",
    description="Admin endpoint to list all user course enrollments with validity information",
)
async def list_course_enrollments(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    course_id: Optional[str] = Query(None, description="Filter by course ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active enrollments"),
    is_expired: Optional[bool] = Query(None, description="Filter by expired enrollments"),
    sort_by: str = Query("enrolled_at", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort order (asc or desc)"),
    page: int = Query(1, description="Page number", ge=1),
    limit: int = Query(10, description="Items per page", ge=1, le=100),
    current_user: User = Depends(admin_required),
):
    """List all course enrollments with filters and pagination (Admin only)"""
    try:
        # Build query filters
        query_filters = {}

        if user_id:
            query_filters["user_id"] = user_id

        if course_id:
            query_filters["course_id"] = course_id

        if is_active is not None:
            query_filters["is_active"] = is_active

        # Calculate pagination
        skip = (page - 1) * limit

        # Set sort order
        sort_direction = 1 if sort_order == "asc" else -1

        # Fetch enrollments with user and course details
        enrollments = await CourseEnrollment.find(query_filters).sort([(sort_by, sort_direction)]).skip(skip).limit(limit).to_list()

        # Get total count for pagination
        total_enrollments = await CourseEnrollment.find(query_filters).count()
        total_pages = (total_enrollments + limit - 1) // limit

        # Enrich enrollments with user and course details
        enriched_enrollments = []
        for enrollment in enrollments:
            # Get user details
            user = await User.get(enrollment.user_id)
            if not user:
                continue

            # Get course details
            course = await Course.get(enrollment.course_id)
            if not course:
                continue

            # Filter by expiration if requested
            if is_expired is not None:
                enrollment_expired = enrollment.is_expired()
                if is_expired != enrollment_expired:
                    continue

            enrollment_data = {
                "id": str(enrollment.id),
                "user_id": enrollment.user_id,
                "user_name": user.name,
                "user_email": user.email,
                "course_id": enrollment.course_id,
                "course_title": course.title,
                "course_code": course.code,
                "enrolled_at": enrollment.enrolled_at,
                "expires_at": enrollment.expires_at,
                "is_active": enrollment.is_active,
                "is_expired": enrollment.is_expired(),
                "days_remaining": enrollment.days_remaining(),
                "enrollment_source": enrollment.enrollment_source,
                "notes": enrollment.notes,
                "created_at": enrollment.created_at,
            }
            enriched_enrollments.append(enrollment_data)

        # Log admin action
        await AdminService.log_admin_action(
            str(current_user.id),
            ActionType.CREATE,
            "course_enrollments",
            "N/A",
            {"action": "list_course_enrollments", "filters": str(query_filters)},
        )

        return AdminService.format_response(
            "Course enrollments retrieved successfully",
            data=enriched_enrollments,
            pagination={
                "total": total_enrollments,
                "page": page,
                "limit": limit,
                "total_pages": total_pages,
            },
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve course enrollments: {str(e)}",
        )


@router.get(
    "/users/{user_id}/enrollments",
    response_model=Dict[str, Any],
    summary="Get user's course enrollments",
    description="Admin endpoint to get all course enrollments for a specific user",
)
async def get_user_course_enrollments(
    user_id: str,
    current_user: User = Depends(admin_required),
):
    """Get all course enrollments for a specific user (Admin only)"""
    try:
        # Verify user exists
        user = await User.get(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Get all enrollments for this user
        enrollments = await CourseEnrollment.find({"user_id": user_id}).sort([("enrolled_at", -1)]).to_list()

        # Enrich with course details
        enriched_enrollments = []
        for enrollment in enrollments:
            course = await Course.get(enrollment.course_id)
            if not course:
                continue

            enrollment_data = {
                "id": str(enrollment.id),
                "course_id": enrollment.course_id,
                "course_title": course.title,
                "course_code": course.code,
                "course_category": course.category.value,
                "enrolled_at": enrollment.enrolled_at,
                "expires_at": enrollment.expires_at,
                "is_active": enrollment.is_active,
                "is_expired": enrollment.is_expired(),
                "days_remaining": enrollment.days_remaining(),
                "enrollment_source": enrollment.enrollment_source,
                "validity_period_days": course.validity_period_days,
            }
            enriched_enrollments.append(enrollment_data)

        # Log admin action
        await AdminService.log_admin_action(
            str(current_user.id),
            ActionType.CREATE,
            "course_enrollments",
            user_id,
            {"action": "get_user_course_enrollments"},
        )

        return AdminService.format_response(
            "User course enrollments retrieved successfully",
            data={
                "user": {
                    "id": str(user.id),
                    "name": user.name,
                    "email": user.email,
                },
                "enrollments": enriched_enrollments,
            },
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve user course enrollments: {str(e)}",
        )


@router.get(
    "/courses/{course_id}/enrollments",
    response_model=Dict[str, Any],
    summary="Get course enrollments",
    description="Admin endpoint to get all enrollments for a specific course",
)
async def get_course_enrollments(
    course_id: str,
    current_user: User = Depends(admin_required),
):
    """Get all enrollments for a specific course (Admin only)"""
    try:
        # Verify course exists
        course = await Course.get(course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found",
            )

        # Get all enrollments for this course
        enrollments = await CourseEnrollment.find({"course_id": course_id}).sort([("enrolled_at", -1)]).to_list()

        # Enrich with user details
        enriched_enrollments = []
        for enrollment in enrollments:
            user = await User.get(enrollment.user_id)
            if not user:
                continue

            enrollment_data = {
                "id": str(enrollment.id),
                "user_id": enrollment.user_id,
                "user_name": user.name,
                "user_email": user.email,
                "enrolled_at": enrollment.enrolled_at,
                "expires_at": enrollment.expires_at,
                "is_active": enrollment.is_active,
                "is_expired": enrollment.is_expired(),
                "days_remaining": enrollment.days_remaining(),
                "enrollment_source": enrollment.enrollment_source,
            }
            enriched_enrollments.append(enrollment_data)

        # Log admin action
        await AdminService.log_admin_action(
            str(current_user.id),
            ActionType.CREATE,
            "course_enrollments",
            course_id,
            {"action": "get_course_enrollments"},
        )

        return AdminService.format_response(
            "Course enrollments retrieved successfully",
            data={
                "course": {
                    "id": str(course.id),
                    "title": course.title,
                    "code": course.code,
                },
                "enrollments": enriched_enrollments,
            },
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve course enrollments: {str(e)}",
        )
