"""
Question management endpoints for admin
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, Dict, Any

from ...models.user import User
from ...dependencies import admin_required
from ...services.admin_service import AdminService
from ...services.question_service import QuestionService
from .schemas import (
    QuestionCreateRequest,
    QuestionUpdateRequest,
    QuestionResponse,
    StandardResponse,
)
from ...models.admin_action import ActionType

router = APIRouter(prefix="/questions", tags=["Admin - Questions"])


@router.get(
    "/{question_id}",
    response_model=Dict[str, Any],
    summary="Get question details",
    description="Admin endpoint to get detailed information about a specific question",
)
async def get_question(
    question_id: str,
    current_user: User = Depends(admin_required),
):
    """Get detailed information about a specific question (Admin only)"""
    try:
        # Find the question
        question = await QuestionService.get_question_by_id(question_id)
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question not found",
            )

        # Convert options to dict format
        options_dict = []
        for option in question.options:
            option_dict = {
                "text": option.text,
                "is_correct": option.is_correct,
                "order": option.order,
                "image_urls": option.image_urls,
            }
            options_dict.append(option_dict)

        # Convert to response format
        question_response = QuestionResponse(
            id=str(question.id),
            title=question.title,
            question_text=question.question_text,
            question_type=question.question_type.value,
            difficulty_level=question.difficulty_level.value,
            exam_year=question.exam_year,
            options=options_dict,
            explanation=question.explanation,
            remarks=question.remarks,
            subject=question.subject,
            topic=question.topic,
            tags=question.tags,
            is_active=question.is_active,
            created_by=question.created_by,
            created_at=question.created_at,
            updated_at=question.updated_at,
            question_image_urls=question.question_image_urls,
            explanation_image_urls=question.explanation_image_urls,
            remarks_image_urls=question.remarks_image_urls,
        )

        return AdminService.format_response(
            "Question details retrieved successfully",
            data=question_response,
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve question details: {str(e)}",
        )


@router.put(
    "/{question_id}",
    response_model=Dict[str, Any],
    summary="Update question",
    description="Admin endpoint to update a question",
)
async def update_question(
    question_id: str,
    question_data: QuestionUpdateRequest,
    current_user: User = Depends(admin_required),
):
    """Update a question (Admin only)"""
    try:
        # Update question data
        question, changes = await QuestionService.update_question_data(
            question_id, question_data.dict(exclude_unset=True)
        )

        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question not found",
            )

        if not changes:
            return AdminService.format_response(
                "No changes to apply",
                question_id=question_id,
            )

        # Log admin action
        await AdminService.log_admin_action(
            str(current_user.id),
            ActionType.UPDATE,
            "questions",
            question_id,
            changes,
        )

        return AdminService.format_response(
            "Question updated successfully",
            question_id=question_id,
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
            detail=f"Failed to update question: {str(e)}",
        )


@router.delete(
    "/{question_id}",
    response_model=Dict[str, Any],
    summary="Delete question",
    description="Admin endpoint to delete a question",
)
async def delete_question(
    question_id: str,
    current_user: User = Depends(admin_required),
):
    """Delete a question (Admin only)"""
    try:
        # Delete question
        question_details = await QuestionService.delete_question(question_id)

        if not question_details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question not found",
            )

        # Log admin action
        await AdminService.log_admin_action(
            str(current_user.id),
            ActionType.DELETE,
            "questions",
            question_id,
            {"deleted_question": question_details},
        )

        return AdminService.format_response(
            "Question deleted successfully",
            question_id=question_id,
            deleted_question=question_details,
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete question: {str(e)}",
        )
