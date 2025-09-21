"""
Course materials router - focused on material and test series management within courses
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import Dict, Any

from ...models.user import User
from ...models.course import Course
from ...models.admin_action import AdminAction, ActionType
from ...dependencies import admin_required
from ...services.admin_service import AdminService

router = APIRouter(prefix="/api/v1/courses", tags=["Courses - Materials"])


@router.post(
    "/{course_id}/materials",
    response_model=Dict[str, Any],
    summary="Add material to course",
    description="Admin endpoint to add study material to a course",
)
async def add_material_to_course(
    course_id: str,
    data: Dict[str, Any],
    current_user: User = Depends(admin_required),
):
    """Add study material to a course (Admin only)"""
    try:
        course = await Course.get(course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found",
            )

        material_id = data.get("material_id")
        if not material_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Material ID is required",
            )

        # Check if material ID already exists in the course
        if material_id in course.material_ids:
            return {
                "message": "Material already added to this course",
                "course_id": course_id,
                "material_id": material_id,
            }

        # Add material to course
        course.material_ids.append(material_id)
        course.update_timestamp()
        await course.save()

        # Log admin action
        await AdminService.log_admin_action(
            str(current_user.id),
            ActionType.UPDATE,
            "courses",
            course_id,
            {"action": "material_added", "material_id": material_id},
        )

        return {
            "message": "Material added to course successfully",
            "course_id": course_id,
            "material_id": material_id,
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add material to course: {str(e)}",
        )


@router.post(
    "/{course_id}/test-series",
    response_model=Dict[str, Any],
    summary="Add test series to course",
    description="Admin endpoint to add test series to a course",
)
async def add_test_series_to_course(
    course_id: str,
    data: Dict[str, Any],
    current_user: User = Depends(admin_required),
):
    """Add test series to a course (Admin only)"""
    try:
        course = await Course.get(course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found",
            )

        test_series_id = data.get("test_series_id")
        if not test_series_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Test series ID is required",
            )

        # Check if test series ID already exists in the course
        if test_series_id in course.test_series_ids:
            return {
                "message": "Test series already added to this course",
                "course_id": course_id,
                "test_series_id": test_series_id,
            }

        # Add test series to course
        course.test_series_ids.append(test_series_id)
        course.update_timestamp()
        await course.save()

        # Log admin action
        await AdminService.log_admin_action(
            str(current_user.id),
            ActionType.UPDATE,
            "courses",
            course_id,
            {"action": "test_series_added", "test_series_id": test_series_id},
        )

        return {
            "message": "Test series added to course successfully",
            "course_id": course_id,
            "test_series_id": test_series_id,
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add test series to course: {str(e)}",
        )


@router.delete(
    "/{course_id}/materials/{material_id}",
    response_model=Dict[str, Any],
    summary="Remove material from course",
    description="Admin endpoint to remove study material from a course",
)
async def remove_material_from_course(
    course_id: str,
    material_id: str,
    current_user: User = Depends(admin_required),
):
    """Remove study material from a course (Admin only)"""
    try:
        course = await Course.get(course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found",
            )

        # Check if material exists in course
        if material_id not in course.material_ids:
            return {
                "message": "Material not found in this course",
                "course_id": course_id,
                "material_id": material_id,
            }

        # Remove material from course
        course.material_ids.remove(material_id)
        course.update_timestamp()
        await course.save()

        # Log admin action
        await AdminService.log_admin_action(
            str(current_user.id),
            ActionType.UPDATE,
            "courses",
            course_id,
            {"action": "material_removed", "material_id": material_id},
        )

        return {
            "message": "Material removed from course successfully",
            "course_id": course_id,
            "material_id": material_id,
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove material from course: {str(e)}",
        )


@router.delete(
    "/{course_id}/test-series/{test_series_id}",
    response_model=Dict[str, Any],
    summary="Remove test series from course",
    description="Admin endpoint to remove a test series from a course",
)
async def remove_test_series_from_course(
    course_id: str,
    test_series_id: str,
    current_user: User = Depends(admin_required),
):
    """Remove test series from a course (Admin only)"""
    try:
        from bson import ObjectId

        # Validate course_id format
        if not ObjectId.is_valid(course_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid course ID format",
            )

        # Find the course
        course = await Course.get(course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
            )

        # Remove test series ID if it exists
        if test_series_id in course.test_series_ids:
            course.test_series_ids.remove(test_series_id)
            await course.save()

        # Log admin action
        await AdminService.log_admin_action(
            str(current_user.id),
            ActionType.UPDATE,
            "courses",
            course_id,
            {"action": "test_series_removed", "test_series_id": test_series_id},
        )

        return {"status": "success", "message": "Test series removed from course"}

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove test series from course: {str(e)}",
        )
