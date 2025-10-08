"""
Course CRUD operations router
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import Optional, Dict, Any

from ...models.course import Course
from ...models.user import User
from ...models.enums import ExamCategory
from ...dependencies import admin_required, get_current_user
from ...services.course_service import CourseService
from .schemas import (
    CourseCreateRequest,
    CourseUpdateRequest,
    CourseResponse,
)

router = APIRouter(prefix="/api/v1/courses", tags=["Courses - CRUD"])


@router.get("/test")
async def test_endpoint():
    """Test endpoint to verify the router is working"""
    return {"message": "Courses router is working", "status": "success"}


@router.post(
    "/",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new course",
    description="Admin endpoint to create a new course",
)
async def create_course(
    course_data: CourseCreateRequest, current_user: User = Depends(admin_required)
):
    """Create a new course (Admin only)"""
    try:
        result = await CourseService.create_course(course_data.dict(), current_user)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create course: {str(e)}",
        )


@router.get(
    "/",
    response_model=Dict[str, Any],
    summary="List all courses",
    description="Get a paginated list of all available courses with optional filters",
)
async def list_courses(
    category: Optional[ExamCategory] = Query(
        None, description="Filter by exam category"
    ),
    search: Optional[str] = Query(None, description="Search in title and description"),
    section: Optional[str] = Query(None, description="Filter by section"),
    is_free: Optional[bool] = Query(None, description="Filter by free courses"),
    is_active: Optional[bool] = Query(True, description="Filter by active status"),
    sort_by: str = Query("priority_order", description="Field to sort by"),
    sort_order: str = Query("asc", description="Sort order (asc or desc)"),
    page: int = Query(1, description="Page number", ge=1),
    limit: int = Query(10, description="Items per page", ge=1, le=100),
    current_user: Optional[User] = Depends(get_current_user),
):
    """List all courses with filters and pagination"""
    try:
        result = await CourseService.list_courses(
            category=category,
            search=search,
            section=section,
            is_free=is_free,
            is_active=is_active,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            limit=limit,
            current_user=current_user,
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve courses: {str(e)}",
        )


@router.get(
    "/enrolled",
    response_model=Dict[str, Any],
    summary="Get enrolled courses",
    description="Get all courses the current user is enrolled in",
)
async def get_enrolled_courses(current_user: User = Depends(get_current_user)):
    """Get courses the current user is enrolled in"""
    try:
        result = await CourseService.get_enrolled_courses(current_user)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve enrolled courses: {str(e)}",
        )


@router.get(
    "/{course_id}",
    response_model=Dict[str, Any],
    summary="Get course details",
    description="Get detailed information about a specific course",
)
async def get_course(course_id: str):
    """Get course details by ID"""
    try:
        result = await CourseService.get_course(course_id)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve course: {str(e)}",
        )


@router.put(
    "/{course_id}",
    response_model=Dict[str, Any],
    summary="Update course",
    description="Admin endpoint to update course details",
)
async def update_course(
    course_id: str,
    course_data: CourseUpdateRequest,
    current_user: User = Depends(admin_required),
):
    """Update course details (Admin only)"""
    try:
        result = await CourseService.update_course(
            course_id, course_data.dict(exclude_unset=True), current_user
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update course: {str(e)}",
        )


@router.delete(
    "/{course_id}",
    response_model=Dict[str, Any],
    summary="Delete course",
    description="Admin endpoint to delete (deactivate) a course",
)
async def delete_course(course_id: str, current_user: User = Depends(admin_required)):
    """Delete (deactivate) a course (Admin only)"""
    try:
        result = await CourseService.delete_course(course_id, current_user)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete course: {str(e)}",
        )


@router.post(
    "/{course_id}/enroll",
    response_model=Dict[str, Any],
    summary="Enroll in course",
    description="Student endpoint to enroll in a course",
)
async def enroll_in_course(
    course_id: str,
    current_user: User = Depends(get_current_user),
):
    """Enroll in a course (Student only)"""
    try:
        result = await CourseService.enroll_user_in_course(course_id, current_user)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enroll in course: {str(e)}",
        )


@router.put(
    "/{course_id}/toggle-visibility",
    response_model=Dict[str, Any],
    summary="Toggle course visibility",
    description="Admin endpoint to toggle course visibility (is_active)",
)
async def toggle_course_visibility(
    course_id: str,
    current_user: User = Depends(admin_required),
):
    """Toggle course visibility (Admin only)"""
    try:
        # Fetch the course
        course = await Course.get(course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found",
            )

        # Toggle visibility
        course.is_active = not course.is_active
        await course.save()

        return {
            "message": f"Course visibility set to {course.is_active}",
            "course": {
                "id": str(course.id),
                "title": course.title,
                "is_active": course.is_active,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to toggle course visibility: {str(e)}",
        )
