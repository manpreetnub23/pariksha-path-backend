from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from ..models.question import Question, QuestionType, DifficultyLevel
from ..models.admin_action import AdminAction, ActionType
from ..models.user import User, UserRole
from ..auth import get_current_user

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


# Request/Response Models for Questions
class OptionModel(BaseModel):
    text: str
    is_correct: bool


class QuestionCreateRequest(BaseModel):
    title: str
    question_text: str
    question_type: QuestionType
    difficulty_level: DifficultyLevel
    exam_type: str
    exam_year: Optional[int] = None
    options: List[OptionModel]
    explanation: Optional[str] = None
    subject: str
    topic: str
    tags: List[str] = []

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Newton's First Law",
                "question_text": "What is Newton's First Law of Motion?",
                "question_type": "mcq",
                "difficulty_level": "medium",
                "exam_type": "JEE Main",
                "exam_year": 2023,
                "options": [
                    {
                        "text": "An object at rest stays at rest unless acted upon by an external force.",
                        "is_correct": True,
                    },
                    {
                        "text": "Force equals mass times acceleration.",
                        "is_correct": False,
                    },
                    {
                        "text": "For every action, there is an equal and opposite reaction.",
                        "is_correct": False,
                    },
                    {
                        "text": "Energy can neither be created nor destroyed.",
                        "is_correct": False,
                    },
                ],
                "explanation": "Newton's First Law states that an object will remain at rest or in uniform motion in a straight line unless acted upon by an external force.",
                "subject": "Physics",
                "topic": "Mechanics",
                "tags": ["newton", "motion", "laws"],
            }
        }


class QuestionUpdateRequest(BaseModel):
    title: Optional[str] = None
    question_text: Optional[str] = None
    question_type: Optional[QuestionType] = None
    difficulty_level: Optional[DifficultyLevel] = None
    exam_type: Optional[str] = None
    exam_year: Optional[int] = None
    options: Optional[List[OptionModel]] = None
    explanation: Optional[str] = None
    subject: Optional[str] = None
    topic: Optional[str] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None


class QuestionResponse(BaseModel):
    id: str
    title: str
    question_text: str
    question_type: str
    difficulty_level: str
    exam_type: str
    exam_year: Optional[int]
    options: List[Dict[str, Any]]
    explanation: Optional[str]
    subject: str
    topic: str
    tags: List[str]
    is_active: bool
    created_by: str
    created_at: datetime
    updated_at: datetime


# Admin-only middleware
async def admin_required(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


# 1. Create Question
@router.post(
    "/questions",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new question",
    description="Admin endpoint to create a new question with multiple options",
)
async def create_question(
    question_data: QuestionCreateRequest, current_user: User = Depends(admin_required)
):
    """
    Create a new question (Admin only)

    The request body must contain all the required question fields including options.
    At least one option must be marked as correct.
    """
    try:
        # Check if at least one option is marked as correct
        has_correct_option = any(option.is_correct for option in question_data.options)
        if not has_correct_option:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one option must be marked as correct",
            )

        # Convert request model to document model
        options_dicts = [
            {"text": opt.text, "is_correct": opt.is_correct}
            for opt in question_data.options
        ]

        # Create the question
        new_question = Question(
            title=question_data.title,
            question_text=question_data.question_text,
            question_type=question_data.question_type,
            difficulty_level=question_data.difficulty_level,
            exam_type=question_data.exam_type,
            exam_year=question_data.exam_year,
            options=options_dicts,
            explanation=question_data.explanation,
            subject=question_data.subject,
            topic=question_data.topic,
            tags=question_data.tags,
            created_by=str(current_user.id),
            is_active=True,
        )

        await new_question.insert()

        # Log admin action
        admin_action = AdminAction(
            admin_id=str(current_user.id),
            action_type=ActionType.CREATE,
            target_collection="questions",
            target_id=str(new_question.id),
            changes={"action": "question_created"},
        )
        await admin_action.insert()

        return {
            "message": "Question created successfully",
            "question_id": str(new_question.id),
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create question: {str(e)}",
        )


# 2. Update Question
@router.put(
    "/questions/{question_id}",
    response_model=Dict[str, Any],
    summary="Update an existing question",
    description="Admin endpoint to update a question's details",
)
async def update_question(
    question_id: str,
    question_data: QuestionUpdateRequest,
    current_user: User = Depends(admin_required),
):
    """
    Update an existing question (Admin only)

    Provide the fields you want to update. If options are provided, all options will be replaced.
    """
    try:
        # Find the question
        question = await Question.get(question_id)
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question not found",
            )

        # Track changes for audit log
        changes = {}

        # Update fields if provided
        for field, value in question_data.dict(exclude_unset=True).items():
            if field == "options" and value is not None:
                # Convert options to dictionary format
                options_dicts = [
                    {"text": opt.text, "is_correct": opt.is_correct} for opt in value
                ]

                # Verify at least one correct option
                has_correct_option = any(opt.is_correct for opt in value)
                if not has_correct_option:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="At least one option must be marked as correct",
                    )

                setattr(question, field, options_dicts)
                changes[field] = "updated"
            elif value is not None:
                setattr(question, field, value)
                changes[field] = value if not isinstance(value, list) else "updated"

        # Update timestamp
        question.update_timestamp()
        await question.save()

        # Log admin action
        admin_action = AdminAction(
            admin_id=str(current_user.id),
            action_type=ActionType.UPDATE,
            target_collection="questions",
            target_id=str(question.id),
            changes=changes,
        )
        await admin_action.insert()

        return {
            "message": "Question updated successfully",
            "question_id": str(question.id),
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update question: {str(e)}",
        )


# 3. Delete Question (soft delete by setting is_active=False)
@router.delete(
    "/questions/{question_id}",
    response_model=Dict[str, Any],
    summary="Delete a question",
    description="Admin endpoint to delete (deactivate) a question",
)
async def delete_question(
    question_id: str, current_user: User = Depends(admin_required)
):
    """
    Delete a question (Admin only)

    This performs a soft delete by setting is_active=False.
    The question will no longer appear in searches but remains in the database.
    """
    try:
        # Find the question
        question = await Question.get(question_id)
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question not found",
            )

        # Soft delete by setting is_active=False
        question.is_active = False
        question.update_timestamp()
        await question.save()

        # Log admin action
        admin_action = AdminAction(
            admin_id=str(current_user.id),
            action_type=ActionType.DELETE,
            target_collection="questions",
            target_id=str(question.id),
            changes={"is_active": False},
        )
        await admin_action.insert()

        return {
            "message": "Question deleted successfully",
            "question_id": str(question.id),
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete question: {str(e)}",
        )
