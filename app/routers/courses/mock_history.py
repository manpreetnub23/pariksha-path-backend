"""
Mock test history router - focused on retrieving user's mock test history
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import Optional, Dict, Any, List

from ...models.user import User
from ...models.test import TestAttempt
from ...dependencies import get_current_user

router = APIRouter(prefix="/api/v1/mock-history", tags=["Mock Test History"])


@router.get("/")
async def get_mock_history(
    current_user: User = Depends(get_current_user),
    limit: int = Query(10, description="Number of results to return", ge=1, le=100),
    skip: int = Query(0, description="Number of results to skip", ge=0),
):
    """Get user's mock test history"""
    try:
        # Get user's test attempts
        attempts = (
            await TestAttempt.find(
                {"user_id": str(current_user.id), "is_completed": True}
            )
            .sort([("end_time", -1)])
            .skip(skip)
            .limit(limit)
            .to_list()
        )

        # Format response
        formatted_attempts = []
        for attempt in attempts:
            # Get course/test information
            course_info = {}
            from ...models.course import Course

            course = await Course.get(attempt.test_series_id)
            if course:
                course_info = {
                    "id": str(course.id),
                    "title": course.title,
                    "code": course.code,
                }

            formatted_attempts.append(
                {
                    "id": str(attempt.id),
                    "date": attempt.end_time,
                    "score": attempt.score,
                    "max_score": attempt.max_score,
                    "percentage": (
                        round((attempt.score / attempt.max_score) * 100, 2)
                        if attempt.max_score > 0
                        else 0
                    ),
                    "accuracy": attempt.accuracy,
                    "total_questions": attempt.total_questions,
                    "attempted_questions": attempt.attempted_questions,
                    "time_spent_seconds": attempt.time_spent_seconds,
                    "course": course_info,
                }
            )

        # Get total count
        total_count = await TestAttempt.find(
            {"user_id": str(current_user.id), "is_completed": True}
        ).count()

        return {
            "message": "Mock test history retrieved successfully",
            "attempts": formatted_attempts,
            "pagination": {
                "total": total_count,
                "skip": skip,
                "limit": limit,
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve mock test history: {str(e)}",
        )


@router.get("/{attempt_id}")
async def get_mock_attempt_details(
    attempt_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get details of a specific mock test attempt"""
    try:
        # Get the test attempt
        attempt = await TestAttempt.get(attempt_id)

        # Check if attempt exists and belongs to current user
        if not attempt or attempt.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Test attempt not found",
            )

        # Get course information
        course_info = {}
        from ...models.course import Course

        course = await Course.get(attempt.test_series_id)
        if course:
            course_info = {
                "id": str(course.id),
                "title": course.title,
                "code": course.code,
            }

        # Format response
        result = {
            "id": str(attempt.id),
            "date": attempt.end_time,
            "score": attempt.score,
            "max_score": attempt.max_score,
            "percentage": (
                round((attempt.score / attempt.max_score) * 100, 2)
                if attempt.max_score > 0
                else 0
            ),
            "accuracy": attempt.accuracy,
            "total_questions": attempt.total_questions,
            "attempted_questions": attempt.attempted_questions,
            "time_spent_seconds": attempt.time_spent_seconds,
            "course": course_info,
            "section_summaries": [
                section.dict() for section in attempt.section_summaries
            ],
            "question_attempts": [qa.dict() for qa in attempt.question_attempts],
        }

        return {
            "message": "Mock test attempt details retrieved successfully",
            "attempt": result,
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve mock test attempt details: {str(e)}",
        )
