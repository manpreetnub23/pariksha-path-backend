"""
Mock test history router - focused on retrieving user's mock test history
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import Optional, Dict, Any, List

from ...models.user import User
from ...models.test import TestAttempt
from ...models.question import Question
from ...dependencies import get_current_user

router = APIRouter(
    prefix="/api/v1/mock-history", tags=["Mock Test History"], redirect_slashes=True
)


@router.get("/")
@router.get("")  # Also handle requests without trailing slash
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
@router.get("/{attempt_id}/")  # Also handle requests with trailing slash
async def get_mock_attempt_details(
    attempt_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get details of a specific mock test attempt with full question data"""
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

        # Get full question data for each question attempt
        question_attempts_with_details = []
        for qa in attempt.question_attempts:
            question = await Question.get(qa.question_id)
            if question:
                # Find the correct option order
                correct_option_order = None
                for opt in question.options:
                    if opt.is_correct:
                        correct_option_order = opt.order
                        break

                # Get selected option order (handle both single and multiple selections)
                selected_option_order = None
                if qa.selected_options and len(qa.selected_options) > 0:
                    # For now, take the first selected option if multiple are selected
                    # You might need to handle this differently based on your question types
                    selected_option_order = int(qa.selected_options[0])

                # Determine if the answer is correct
                is_correct = qa.status == "correct"

                question_attempts_with_details.append(
                    {
                        "question_id": qa.question_id,
                        "selected_option_order": selected_option_order,
                        "correct_option_order": correct_option_order,
                        "is_correct": is_correct,
                        "status": (
                            qa.status.value
                            if hasattr(qa.status, "value")
                            else str(qa.status)
                        ),
                        "selected_options": qa.selected_options,  # Keep original for debugging
                        "time_spent_seconds": qa.time_spent_seconds,
                        "marks_awarded": qa.marks_awarded,
                        "marks_available": qa.marks_available,
                        "negative_marks": qa.negative_marks,
                        "question": {
                            "id": str(question.id),
                            "title": question.title,
                            "question_text": question.question_text,
                            "question_type": getattr(
                                question.question_type, "value", str(question.question_type)
                            ),
                            "difficulty_level": getattr(
                                question.difficulty_level,
                                "value",
                                str(question.difficulty_level),
                            ),
                            "section": getattr(question, "section", None),
                            "options": [
                                {
                                    "text": opt.text,
                                    "is_correct": opt.is_correct,
                                    "order": opt.order,
                                    "image_urls": opt.image_urls,
                                }
                                for opt in sorted(
                                    question.options, key=lambda x: x.order
                                )
                            ],
                            "explanation": question.explanation,
                            "remarks": getattr(question, "remarks", None),
                            "subject": question.subject,
                            "topic": question.topic,
                            "tags": getattr(question, "tags", []),
                            "marks": getattr(question, "marks", 1.0),
                            "question_image_urls": question.question_image_urls,
                            "explanation_image_urls": getattr(
                                question, "explanation_image_urls", []
                            ),
                            "remarks_image_urls": getattr(
                                question, "remarks_image_urls", []
                            ),
                            "created_at": getattr(question, "created_at", None),
                            "updated_at": getattr(question, "updated_at", None),
                            "is_active": getattr(question, "is_active", True),
                            "created_by": getattr(question, "created_by", None),
                        },
                    }
                )

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
            "question_attempts": question_attempts_with_details,
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
