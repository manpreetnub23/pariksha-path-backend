"""
Mock tests router - focused on mock testing functionality
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import Optional, Dict, Any, List

from ...models.user import User
from ...dependencies import get_current_user
from ...services.mock_test_service import MockTestService
from .schemas import MockSubmitRequest

router = APIRouter(prefix="/api/v1/courses", tags=["Courses - Mock Tests"])


@router.get("/tests")
async def list_tests(is_free: Optional[str] = None):
    """List available tests"""
    try:
        result = await MockTestService.list_tests(is_free)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve tests: {str(e)}",
        )


@router.post(
    "/{course_id}/mock/submit",
    response_model=Dict[str, Any],
    summary="Submit course-based mock answers",
    description=(
        "Submit answers for a course/section-based mock test and receive scored results.\n"
        "Accepts either selected_option_order or selected_option_text for each answer."
    ),
)
async def submit_course_mock(
    course_id: str,
    payload: MockSubmitRequest,
    current_user: User = Depends(get_current_user),
):
    """Score submitted answers for a course-based mock without persisting attempts."""
    try:
        result = await MockTestService.submit_course_mock(
            course_id=course_id,
            answers=[answer.dict() for answer in payload.answers],
            time_spent_seconds=payload.time_spent_seconds or 0,
            current_user=current_user,
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit mock answers: {str(e)}",
        )
