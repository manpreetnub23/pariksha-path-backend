"""
Student management endpoints for admin
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, Dict, Any

from ...models.user import User
from ...models.enums import UserRole, ExamCategory
from ...dependencies import admin_required
from ...services.admin_service import AdminService
from ...services.student_service import StudentService
from .schemas import (
    StudentUpdateRequest,
    StudentResponse,
    PasswordResetRequest,
    StandardResponse,
)
from ...models.admin_action import ActionType

router = APIRouter(prefix="/students", tags=["Admin - Students"])


@router.get(
    "/",
    response_model=Dict[str, Any],
    summary="List all students",
    description="Admin endpoint to list all students with filters and pagination",
)
async def list_students(
    search: Optional[str] = Query(None, description="Search by name or email"),
    exam_category: Optional[ExamCategory] = Query(
        None, description="Filter by exam category"
    ),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_verified: Optional[bool] = Query(
        None, description="Filter by verification status"
    ),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort order (asc or desc)"),
    page: int = Query(1, description="Page number", ge=1),
    limit: int = Query(10, description="Items per page", ge=1, le=100),
    current_user: User = Depends(admin_required),
):
    """List all students with filters and pagination (Admin only)"""
    try:
        # Build query filters
        query_filters = AdminService.build_query_filters(
            base_filters={"role": UserRole.STUDENT},
            search=search,
            search_fields=["name", "email"],
            exam_category=exam_category,
            is_active=is_active,
            is_verified=is_verified,
        )

        # Get students with pagination
        students, pagination = await StudentService.get_students_with_filters(
            query_filters, {"page": page, "limit": limit}, sort_by, sort_order
        )

        # Log admin action
        await AdminService.log_admin_action(
            str(current_user.id),
            ActionType.CREATE,
            "users",
            "N/A",
            {"action": "list_students", "filters": str(query_filters)},
        )

        return AdminService.format_response(
            "Students retrieved successfully",
            data=students,
            pagination=pagination,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve students: {str(e)}",
        )


@router.get(
    "/{student_id}",
    response_model=Dict[str, Any],
    summary="Get student details",
    description="Admin endpoint to get detailed information about a specific student",
)
async def get_student(
    student_id: str,
    current_user: User = Depends(admin_required),
):
    """Get detailed information about a specific student (Admin only)"""
    try:
        # Find the student
        student = await StudentService.get_student_by_id(student_id)
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found",
            )

        # Convert to response format
        student_response = {
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

        # Get additional details
        additional_info = await StudentService.get_student_additional_info(student_id)

        # Log admin action
        await AdminService.log_admin_action(
            str(current_user.id),
            ActionType.CREATE,
            "users",
            student_id,
            {"action": "get_student_details"},
        )

        return AdminService.format_response(
            "Student details retrieved successfully",
            data={
                "student": student_response,
                "additional_info": additional_info,
            },
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve student details: {str(e)}",
        )


@router.put(
    "/{student_id}",
    response_model=Dict[str, Any],
    summary="Update student information",
    description="Admin endpoint to update a student's profile information",
)
async def update_student(
    student_id: str,
    update_data: StudentUpdateRequest,
    current_user: User = Depends(admin_required),
):
    """Update a student's profile information (Admin only)"""
    try:
        # Update student data
        student, changes = await StudentService.update_student_data(
            student_id, update_data.dict(exclude_unset=True)
        )

        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found",
            )

        if not changes:
            return AdminService.format_response(
                "No changes to apply",
                student_id=student_id,
            )

        # Log admin action
        await AdminService.log_admin_action(
            str(current_user.id),
            ActionType.UPDATE,
            "users",
            student_id,
            changes,
        )

        # Create response
        student_response = {
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

        return AdminService.format_response(
            "Student updated successfully",
            data=student_response,
            changes=changes,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update student: {str(e)}",
        )


@router.delete(
    "/{student_id}",
    response_model=Dict[str, Any],
    summary="Deactivate student",
    description="Admin endpoint to deactivate a student (soft delete)",
)
async def deactivate_student(
    student_id: str,
    current_user: User = Depends(admin_required),
):
    """Deactivate a student (Admin only)"""
    try:
        # Deactivate student
        deactivated = await StudentService.deactivate_student(student_id)

        if not deactivated:
            # Check if student exists
            student = await StudentService.get_student_by_id(student_id)
            if not student:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Student not found",
                )
            else:
                return AdminService.format_response(
                    "Student is already deactivated",
                    student_id=student_id,
                )

        # Log admin action
        await AdminService.log_admin_action(
            str(current_user.id),
            ActionType.DELETE,
            "users",
            student_id,
            {"is_active": False},
        )

        return AdminService.format_response(
            "Student deactivated successfully",
            student_id=student_id,
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deactivate student: {str(e)}",
        )


@router.post(
    "/{student_id}/reset-password",
    response_model=Dict[str, Any],
    summary="Reset student password",
    description="Admin endpoint to reset a student's password",
)
async def reset_student_password(
    student_id: str,
    password_data: PasswordResetRequest,
    current_user: User = Depends(admin_required),
):
    """Reset a student's password (Admin only)"""
    try:
        # Reset password
        success = await StudentService.reset_student_password(
            student_id, password_data.new_password
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found",
            )

        # Log admin action
        await AdminService.log_admin_action(
            str(current_user.id),
            ActionType.UPDATE,
            "users",
            student_id,
            {"action": "password_reset"},
        )

        return AdminService.format_response(
            "Student password reset successfully",
            student_id=student_id,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset student password: {str(e)}",
        )


@router.get(
    "/{student_id}/analytics",
    response_model=Dict[str, Any],
    summary="Get student analytics",
    description="Admin endpoint to view a student's performance analytics",
)
async def get_student_analytics(
    student_id: str,
    current_user: User = Depends(admin_required),
):
    """Get a student's performance analytics (Admin only)"""
    try:
        # Get analytics data
        student_info, analytics_data = await StudentService.get_student_analytics(
            student_id
        )

        if not student_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found",
            )

        # Log admin action
        await AdminService.log_admin_action(
            str(current_user.id),
            ActionType.CREATE,
            "user_analytics",
            student_id,
            {"action": "view_analytics"},
        )

        return AdminService.format_response(
            "Student analytics retrieved successfully",
            data={
                "student": student_info,
                "analytics": analytics_data,
            },
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve student analytics: {str(e)}",
        )
