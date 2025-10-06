"""
CSV import endpoints for admin
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import Optional, Dict, Any
import pandas as pd
import io

from ...models.user import User
from ...models.enums import ExamCategory
from ...dependencies import admin_required
from ...services.admin_service import AdminService
from ...services.question_service import QuestionService
from ...models.admin_action import ActionType
from ...models.question import DifficultyLevel
from ...models.test import TestDifficulty

router = APIRouter(prefix="/import", tags=["Admin - CSV Import"])


@router.post(
    "/questions",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Import questions from CSV",
    description="Import questions from CSV file and create/update a test",
)
async def import_questions_from_csv(
    file: UploadFile = File(...),
    test_title: str = Form(...),
    exam_category: str = Form(...),
    exam_subcategory: str = Form(...),
    subject: str = Form(...),
    topic: Optional[str] = Form(None),
    difficulty: str = Form("MEDIUM"),
    duration_minutes: int = Form(60),
    is_free: str = Form("false"),
    existing_test_id: Optional[str] = Form(None),
    current_user: User = Depends(admin_required),
):
    """
    Import questions from CSV file and create/update a test.

    The CSV should have the following columns:
    - Question
    - Option A
    - Option B
    - Option C
    - Option D
    - Correct Answer (A, B, C, or D)
    - Explanation (optional)
    - Remarks (optional)
    - marks (required, marks value for each question)

    Images can be included as URLs in any field.
    """
    try:
        # Check if file is provided
        if not file:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="No file provided"
            )

        # Read and validate file content
        contents = await file.read()
        if not contents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty file provided",
            )

        # Try to read CSV with different encodings if needed
        try:
            df = pd.read_csv(io.BytesIO(contents))
        except Exception as e:
            # Try with different encodings
            for encoding in ["utf-8", "latin1", "iso-8859-1", "cp1252"]:
                try:
                    df = pd.read_csv(io.BytesIO(contents), encoding=encoding)
                    break
                except:
                    continue
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Could not read CSV file with any standard encoding",
                )

        # Validate CSV structure
        required_columns = [
            "Question",
            "Option A",
            "Option B",
            "Option C",
            "Option D",
            "Correct Answer",
            "marks",
        ]

        for col in required_columns:
            if col not in df.columns:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required column: {col}",
                )

        # Normalize enum values
        exam_category_enum = AdminService.normalize_enum(exam_category, ExamCategory)
        difficulty_enum = AdminService.normalize_enum(difficulty, DifficultyLevel)
        test_difficulty_enum = AdminService.normalize_enum(difficulty, TestDifficulty)
        is_free_bool = is_free.lower() in ("true", "1", "yes", "on")

        # Process questions
        questions, errors = await QuestionService.process_csv_questions(
            df=df,
            exam_category=exam_category_enum,
            exam_subcategory=exam_subcategory,
            subject=subject,
            topic=topic,
            difficulty=difficulty_enum,
            created_by=str(current_user.id),
        )

        # Create or update test series
        test_series = await QuestionService.create_or_update_test_with_questions(
            questions=questions,
            test_title=test_title,
            exam_category=exam_category_enum,
            exam_subcategory=exam_subcategory,
            subject=subject,
            duration_minutes=duration_minutes,
            is_free=is_free_bool,
            created_by=str(current_user.id),
            existing_test_id=existing_test_id,
        )

        # Log admin action
        await AdminService.log_admin_action(
            str(current_user.id),
            ActionType.CREATE if not existing_test_id else ActionType.UPDATE,
            "test_series",
            str(test_series.id),
            {
                "action": "import_questions",
                "questions_added": len(questions),
                "source": file.filename,
            },
        )

        return AdminService.format_response(
            f"Successfully imported {len(questions)} questions",
            data={
                "test_id": str(test_series.id),
                "test_title": test_series.title,
                "questions_imported": len(questions),
                "errors": errors if errors else None,
            },
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import questions: {str(e)}",
        )


@router.get(
    "/tests/{test_id}/questions",
    response_model=Dict[str, Any],
    summary="Get test questions",
    description="Admin endpoint to view all questions in a test",
)
async def get_test_questions(
    test_id: str, current_user: User = Depends(admin_required)
):
    """Get all questions for a specific test"""
    try:
        from ...models.test import TestSeries

        # Get test
        test = await TestSeries.get(test_id)
        if not test:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Test not found"
            )

        # Get questions
        questions = await QuestionService.get_questions_for_test(test_id)

        # Format response
        question_data = [
            {
                "id": str(q.id),
                "title": q.title,
                "question_text": q.question_text,
                "options": q.options,
                "explanation": q.explanation,
                "subject": q.subject,
                "topic": q.topic,
                "difficulty_level": q.difficulty_level,
                "metadata": getattr(q, "metadata", None),
            }
            for q in questions
        ]

        return AdminService.format_response(
            "Test questions retrieved successfully",
            data={
                "test": {
                    "id": str(test.id),
                    "title": test.title,
                    "exam_category": test.exam_category,
                    "exam_subcategory": test.exam_subcategory,
                    "total_questions": test.total_questions,
                    "duration_minutes": test.duration_minutes,
                },
                "questions": question_data,
            },
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve test questions: {str(e)}",
        )
