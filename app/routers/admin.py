from datetime import datetime, timezone
import io
import re
import pandas as pd
from typing import List, Optional, Dict, Any

from fastapi import (
    APIRouter,
    HTTPException,
    Depends,
    status,
    Query,
    UploadFile,
    File,
    Form,
    Request,
)
from pydantic import BaseModel, EmailStr

from ..models.test import TestSeries, TestDifficulty
from ..models.question import Question, QuestionType, DifficultyLevel
from ..models.admin_action import AdminAction, ActionType
from ..models.user import User
from ..models.enums import UserRole, ExamCategory
from ..models.user_analytics import UserAnalytics
from ..auth import AuthService, UserRegisterRequest
from ..dependencies import admin_required, get_current_user

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


# Student Management Request/Response Models
class StudentUpdateRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None
    preferred_exam_categories: Optional[List[ExamCategory]] = None
    is_verified: Optional[bool] = None


class StudentResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    phone: str
    role: str
    is_active: bool
    is_verified: bool
    is_email_verified: bool
    preferred_exam_categories: List[str]
    enrolled_courses: List[str]
    created_at: datetime
    last_login: Optional[datetime] = None


class StudentFilterParams(BaseModel):
    search: Optional[str] = None
    exam_category: Optional[ExamCategory] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    sort_by: Optional[str] = "created_at"
    sort_order: Optional[str] = "desc"


class PasswordResetRequest(BaseModel):
    new_password: str


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


# Helper function to extract image URLs from text
def extract_image_urls(text):
    if not isinstance(text, str):
        return text, []

    # Pattern to match URLs
    url_pattern = r"https?://\S+"
    urls = re.findall(url_pattern, text)

    # Remove URLs from text
    clean_text = re.sub(url_pattern, "", text).strip()

    return clean_text, urls


# Student Management Routes


@router.get(
    "/students",
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
        query_filters = {"role": UserRole.STUDENT}

        if search:
            # Search in name or email
            query_filters["$or"] = [
                {"name": {"$regex": search, "$options": "i"}},
                {"email": {"$regex": search, "$options": "i"}},
            ]

        if exam_category:
            query_filters["preferred_exam_categories"] = exam_category

        if is_active is not None:
            query_filters["is_active"] = is_active

        if is_verified is not None:
            query_filters["is_verified"] = is_verified

        # Calculate pagination
        skip = (page - 1) * limit

        # Set sort order
        sort_direction = -1 if sort_order == "desc" else 1

        # Fetch users
        students = (
            await User.find(query_filters)
            .sort([(sort_by, sort_direction)])
            .skip(skip)
            .limit(limit)
            .to_list()
        )

        # Count total matching users for pagination info
        total_students = await User.find(query_filters).count()
        total_pages = (total_students + limit - 1) // limit

        # Convert user objects to response format
        student_responses = [
            StudentResponse(
                id=str(student.id),
                name=student.name,
                email=student.email,
                phone=student.phone,
                role=student.role.value,
                is_active=student.is_active,
                is_verified=student.is_verified,
                is_email_verified=student.is_email_verified,
                preferred_exam_categories=[
                    cat.value for cat in student.preferred_exam_categories
                ],
                enrolled_courses=student.enrolled_courses,
                created_at=student.created_at,
                last_login=student.last_login,
            )
            for student in students
        ]

        # Log admin action
        admin_action = AdminAction(
            admin_id=str(current_user.id),
            action_type=ActionType.CREATE,
            target_collection="users",
            target_id="N/A",
            changes={"action": "list_students", "filters": str(query_filters)},
        )
        await admin_action.insert()

        return {
            "message": "Students retrieved successfully",
            "data": student_responses,
            "pagination": {
                "total": total_students,
                "page": page,
                "limit": limit,
                "total_pages": total_pages,
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve students: {str(e)}",
        )


@router.get(
    "/students/{student_id}",
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
        # Find the student by ID
        student = await User.get(student_id)
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found",
            )

        # Check if the user is actually a student
        if student.role != UserRole.STUDENT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is not a student",
            )

        # Convert to response model
        student_response = StudentResponse(
            id=str(student.id),
            name=student.name,
            email=student.email,
            phone=student.phone,
            role=student.role.value,
            is_active=student.is_active,
            is_verified=student.is_verified,
            is_email_verified=student.is_email_verified,
            preferred_exam_categories=[
                cat.value for cat in student.preferred_exam_categories
            ],
            enrolled_courses=student.enrolled_courses,
            created_at=student.created_at,
            last_login=student.last_login,
        )

        # Get additional details about purchases, test attempts, etc.
        additional_info = {
            "purchased_test_series": student.purchased_test_series,
            "purchased_materials": student.purchased_materials,
            "has_premium_access": student.has_premium_access,
            "completed_tests": len(student.completed_tests),
            "dashboard_settings": student.dashboard_settings,
        }

        # Log admin action
        admin_action = AdminAction(
            admin_id=str(current_user.id),
            action_type=ActionType.CREATE,
            target_collection="users",
            target_id=student_id,
            changes={"action": "get_student_details"},
        )
        await admin_action.insert()

        return {
            "message": "Student details retrieved successfully",
            "student": student_response,
            "additional_info": additional_info,
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve student details: {str(e)}",
        )


@router.put(
    "/students/{student_id}",
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
        # Find the student
        student = await User.get(student_id)
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found",
            )

        # Check if the user is actually a student
        if student.role != UserRole.STUDENT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is not a student",
            )

        # Track changes for audit log
        changes = {}

        # Update fields if provided
        update_dict = update_data.dict(exclude_unset=True)

        for field, value in update_dict.items():
            if value is not None:
                # Special validation for phone if provided
                if field == "phone" and value != student.phone:
                    # Check if phone already exists for another user
                    existing_phone = await User.find_one(
                        {"phone": value, "_id": {"$ne": student.id}}
                    )
                    if existing_phone:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Phone number already exists",
                        )

                # Set the new value
                setattr(student, field, value)
                changes[field] = str(value)

        # Only update if there are changes
        if changes:
            student.update_timestamp()
            await student.save()

            # Log admin action
            admin_action = AdminAction(
                admin_id=str(current_user.id),
                action_type=ActionType.UPDATE,
                target_collection="users",
                target_id=student_id,
                changes=changes,
            )
            await admin_action.insert()

            # Create response
            student_response = StudentResponse(
                id=str(student.id),
                name=student.name,
                email=student.email,
                phone=student.phone,
                role=student.role.value,
                is_active=student.is_active,
                is_verified=student.is_verified,
                is_email_verified=student.is_email_verified,
                preferred_exam_categories=[
                    cat.value for cat in student.preferred_exam_categories
                ],
                enrolled_courses=student.enrolled_courses,
                created_at=student.created_at,
                last_login=student.last_login,
            )

            return {
                "message": "Student updated successfully",
                "student": student_response,
                "changes": changes,
            }
        else:
            return {
                "message": "No changes to apply",
                "student_id": student_id,
            }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update student: {str(e)}",
        )


@router.delete(
    "/students/{student_id}",
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
        # Find the student
        student = await User.get(student_id)
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found",
            )

        # Check if the user is actually a student
        if student.role != UserRole.STUDENT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is not a student",
            )

        # Check if student is already inactive
        if not student.is_active:
            return {
                "message": "Student is already deactivated",
                "student_id": student_id,
            }

        # Soft delete by setting is_active=False
        student.is_active = False
        student.update_timestamp()
        await student.save()

        # Log admin action
        admin_action = AdminAction(
            admin_id=str(current_user.id),
            action_type=ActionType.DELETE,
            target_collection="users",
            target_id=student_id,
            changes={"is_active": False},
        )
        await admin_action.insert()

        return {
            "message": "Student deactivated successfully",
            "student_id": student_id,
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deactivate student: {str(e)}",
        )


@router.post(
    "/students/{student_id}/reset-password",
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
        # Find the student
        student = await User.get(student_id)
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found",
            )

        # Check if the user is actually a student
        if student.role != UserRole.STUDENT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is not a student",
            )

        # Validate new password
        if not AuthService.validate_password(password_data.new_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters long and contain uppercase, lowercase, number, and special character",
            )

        # Update password
        student.password_hash = AuthService.get_password_hash(
            password_data.new_password
        )
        student.update_timestamp()
        await student.save()

        # Log admin action
        admin_action = AdminAction(
            admin_id=str(current_user.id),
            action_type=ActionType.UPDATE,
            target_collection="users",
            target_id=student_id,
            changes={"action": "password_reset"},
        )
        await admin_action.insert()

        return {
            "message": "Student password reset successfully",
            "student_id": student_id,
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset student password: {str(e)}",
        )


@router.get(
    "/students/{student_id}/analytics",
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
        # Find the student
        student = await User.get(student_id)
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found",
            )

        # Check if the user is actually a student
        if student.role != UserRole.STUDENT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is not a student",
            )

        # Get analytics data from UserAnalytics collection
        analytics = await UserAnalytics.find_one({"user_id": student_id})

        if not analytics:
            # Create a new analytics record if none exists
            analytics = UserAnalytics(user_id=student_id)
            await analytics.insert()

        # Basic student info
        student_info = {
            "id": str(student.id),
            "name": student.name,
            "email": student.email,
            "preferred_exam_categories": [
                cat.value for cat in student.preferred_exam_categories
            ],
        }

        # Format analytics data
        analytics_data = {
            # Test performance
            "tests_taken": analytics.tests_taken,
            "tests_passed": analytics.tests_passed,
            "avg_accuracy": analytics.avg_accuracy,
            "avg_test_score": analytics.avg_test_score,
            "avg_percentile": analytics.avg_percentile,
            "best_percentile": analytics.best_percentile,
            # Subject performance
            "subject_performance": analytics.subject_performance,
            "strongest_subjects": analytics.strongest_subjects,
            "weakest_subjects": analytics.weakest_subjects,
            # Time and engagement
            "total_study_time_minutes": analytics.total_study_time_minutes,
            "study_habits": analytics.study_habits.dict(),
            "materials_accessed": analytics.materials_accessed,
            "materials_completed": analytics.materials_completed,
            # Detailed breakdowns
            "difficulty_performance": analytics.difficulty_performance,
            "exam_readiness": analytics.exam_readiness,
            # Last update time
            "last_updated": analytics.last_updated,
        }

        # Log admin action
        admin_action = AdminAction(
            admin_id=str(current_user.id),
            action_type=ActionType.CREATE,
            target_collection="user_analytics",
            target_id=student_id,
            changes={"action": "view_analytics"},
        )
        await admin_action.insert()

        return {
            "message": "Student analytics retrieved successfully",
            "student": student_info,
            "analytics": analytics_data,
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve student analytics: {str(e)}",
        )


# # 1. Create Question
# @router.post(
#     "/questions",
#     response_model=Dict[str, Any],
#     status_code=status.HTTP_201_CREATED,
#     summary="Create a new question",
#     description="Admin endpoint to create a new question with multiple options",
# )
# async def create_question(
#     question_data: QuestionCreateRequest, current_user: User = Depends(admin_required)
# ):
#     """
#     Create a new question (Admin only)

#     The request body must contain all the required question fields including options.
#     At least one option must be marked as correct.
#     """
#     try:
#         # Check if at least one option is marked as correct
#         has_correct_option = any(option.is_correct for option in question_data.options)
#         if not has_correct_option:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="At least one option must be marked as correct",
#             )

#         # Convert request model to document model
#         options_dicts = [
#             {"text": opt.text, "is_correct": opt.is_correct}
#             for opt in question_data.options
#         ]

#         # Create the question
#         new_question = Question(
#             title=question_data.title,
#             question_text=question_data.question_text,
#             question_type=question_data.question_type,
#             difficulty_level=question_data.difficulty_level,
#             exam_type=question_data.exam_type,
#             exam_year=question_data.exam_year,
#             options=options_dicts,
#             explanation=question_data.explanation,
#             subject=question_data.subject,
#             topic=question_data.topic,
#             tags=question_data.tags,
#             created_by=str(current_user.id),
#             is_active=True,
#         )

#         await new_question.insert()

#         # Log admin action
#         admin_action = AdminAction(
#             admin_id=str(current_user.id),
#             action_type=ActionType.CREATE,
#             target_collection="questions",
#             target_id=str(new_question.id),
#             changes={"action": "question_created"},
#         )
#         await admin_action.insert()

#         return {
#             "message": "Question created successfully",
#             "question_id": str(new_question.id),
#         }

#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to create question: {str(e)}",
#         )


# # 2. Update Question
# @router.put(
#     "/questions/{question_id}",
#     response_model=Dict[str, Any],
#     summary="Update an existing question",
#     description="Admin endpoint to update a question's details",
# )
# async def update_question(
#     question_id: str,
#     question_data: QuestionUpdateRequest,
#     current_user: User = Depends(admin_required),
# ):
#     """
#     Update an existing question (Admin only)

#     Provide the fields you want to update. If options are provided, all options will be replaced.
#     """
#     try:
#         # Find the question
#         question = await Question.get(question_id)
#         if not question:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="Question not found",
#             )

#         # Track changes for audit log
#         changes = {}

#         # Update fields if provided
#         for field, value in question_data.dict(exclude_unset=True).items():
#             if field == "options" and value is not None:
#                 # Convert options to dictionary format
#                 options_dicts = [
#                     {"text": opt.text, "is_correct": opt.is_correct} for opt in value
#                 ]

#                 # Verify at least one correct option
#                 has_correct_option = any(opt.is_correct for opt in value)
#                 if not has_correct_option:
#                     raise HTTPException(
#                         status_code=status.HTTP_400_BAD_REQUEST,
#                         detail="At least one option must be marked as correct",
#                     )

#                 setattr(question, field, options_dicts)
#                 changes[field] = "updated"
#             elif value is not None:
#                 setattr(question, field, value)
#                 changes[field] = value if not isinstance(value, list) else "updated"

#         # Update timestamp
#         question.update_timestamp()
#         await question.save()

#         # Log admin action
#         admin_action = AdminAction(
#             admin_id=str(current_user.id),
#             action_type=ActionType.UPDATE,
#             target_collection="questions",
#             target_id=str(question.id),
#             changes=changes,
#         )
#         await admin_action.insert()

#         return {
#             "message": "Question updated successfully",
#             "question_id": str(question.id),
#         }

#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to update question: {str(e)}",
#         )


# # 3. Delete Question (soft delete by setting is_active=False)
# @router.delete(
#     "/questions/{question_id}",
#     response_model=Dict[str, Any],
#     summary="Delete a question",
#     description="Admin endpoint to delete (deactivate) a question",
# )
# async def delete_question(
#     question_id: str, current_user: User = Depends(admin_required)
# ):
#     """
#     Delete a question (Admin only)

#     This performs a soft delete by setting is_active=False.
#     The question will no longer appear in searches but remains in the database.
#     """
#     try:
#         # Find the question
#         question = await Question.get(question_id)
#         if not question:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="Question not found",
#             )

#         # Soft delete by setting is_active=False
#         question.is_active = False
#         question.update_timestamp()
#         await question.save()

#         # Log admin action
#         admin_action = AdminAction(
#             admin_id=str(current_user.id),
#             action_type=ActionType.DELETE,
#             target_collection="questions",
#             target_id=str(question.id),
#             changes={"is_active": False},
#         )
#         await admin_action.insert()

#         return {
#             "message": "Question deleted successfully",
#             "question_id": str(question.id),
#         }

#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to delete question: {str(e)}",
#         )


# @router.post("/import-questions")
# async def import_questions_from_csv(request: Request):
#     form = await request.form()
#     print(form)

# @router.post(
#     "/import-questions",
#     response_model=dict,
#     status_code=status.HTTP_201_CREATED,
# )
# async def import_questions_from_csv(
#     file: UploadFile = File(...),
#     test_title: str = Form(...),
#     exam_category: str = Form(...),
#     exam_subcategory: str = Form(...),
#     subject: str = Form(...),
#     topic: Optional[str] = Form(None),
#     difficulty: str = Form("MEDIUM"),
#     duration_minutes: int = Form(60),
#     is_free: str = Form("false"),
#     existing_test_id: Optional[str] = Form(None),
#     current_user: User = Depends(admin_required),
# ):
#     # Normalize raw inputs
#     raw_exam_category = exam_category.strip()
#     raw_difficulty = difficulty.strip()
#     raw_is_free = is_free.strip().lower()

#     # Case-insensitive enum matching


@router.post(
    "/import-questions",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
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

    def normalize_enum(value: str, enum_cls):
        for member in enum_cls:
            if value.lower() == member.value.lower():
                return member
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {enum_cls.__name__}: {value}. "
            f"Allowed: {[m.value for m in enum_cls]}",
        )

    # Normalize raw inputs
    raw_exam_category = exam_category.strip()
    raw_difficulty = difficulty.strip()
    raw_is_free = is_free.strip().lower()

    # Convert to enum types
    exam_category_enum = normalize_enum(raw_exam_category, ExamCategory)
    difficulty_enum = normalize_enum(raw_difficulty, DifficultyLevel)
    test_difficulty_enum = normalize_enum(raw_difficulty, TestDifficulty)
    is_free_bool = raw_is_free in ("true", "1", "yes", "on")

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

    Images can be included as URLs in any field.
    """
    print("\n=== Starting import_questions_from_csv ===")

    # For now, return a success response since the actual CSV processing is commented out

    try:
        # Debug: Log incoming form data
        print("\n=== Incoming Request Data ===")
        print(f"Test Title: {test_title}")
        print(f"Exam Category: {exam_category} (type: {type(exam_category)})")
        print(f"Exam Subcategory: {exam_subcategory} (type: {type(exam_subcategory)})")
        print(f"Subject: {subject} (type: {type(subject)})")
        print(f"Topic: {topic} (type: {type(topic)})")
        print(f"Difficulty: {difficulty} (type: {type(difficulty)})")
        print(f"Duration: {duration_minutes} minutes (type: {type(duration_minutes)})")
        print(f"Is Free: {is_free} (type: {type(is_free)})")
        print(f"Existing Test ID: {existing_test_id} (type: {type(existing_test_id)})")

        print("\n=== File Info ===")
        print(f"Filename: {file.filename} (type: {type(file.filename)})")
        print(f"Content Type: {file.content_type} (type: {type(file.content_type)})")

        # Check if file is provided
        if not file:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="No file provided"
            )
        else:
            print(f"File provided: {file.filename} (type: {type(file.filename)})")
        # Read and validate file content
        try:
            contents = await file.read()
            if not contents:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Empty file provided",
                )

            print(
                f"\n=== First 200 chars of file ===\n{contents[:200].decode('utf-8', errors='replace')}..."
            )

            # Try to read CSV with different encodings if needed
            try:
                df = pd.read_csv(io.BytesIO(contents))
            except Exception as e:
                print(f"Error reading CSV with default encoding: {str(e)}")
                # Try with different encodings
                for encoding in ["utf-8", "latin1", "iso-8859-1", "cp1252"]:
                    try:
                        df = pd.read_csv(io.BytesIO(contents), encoding=encoding)
                        print(f"Successfully read CSV with {encoding} encoding")
                        break
                    except:
                        continue
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Could not read CSV file with any standard encoding",
                    )

            print("\n=== CSV Headers ===")
            print(df.columns.tolist())
            print("\n=== First row ===")
            print(df.iloc[0].to_dict() if not df.empty else "Empty DataFrame")

        except Exception as e:
            print(f"Error processing file: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error processing file: {str(e)}",
            )

        # Validate CSV structure
        required_columns = [
            "Question",
            "Option A",
            "Option B",
            "Option C",
            "Option D",
            "Correct Answer",
        ]
        print("Validated")
        for col in required_columns:
            if col not in df.columns:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required column: {col}",
                )

        # Process questions
        questions = []
        errors = []

        for idx, row in df.iterrows():
            try:
                print("Start")
                print(idx, row)
                # Extract image URLs from question text
                question_text, question_images = extract_image_urls(row["Question"])

                # Process options and extract image URLs
                options = []
                for opt in ["A", "B", "C", "D"]:
                    option_text, option_images = extract_image_urls(
                        row[f"Option {opt}"]
                    )
                    is_correct = str(row["Correct Answer"]).strip().upper() == opt

                option_data = {
                    "text": option_text,
                    "is_correct": is_correct,
                }

                # Add image URLs if present
                if option_images:
                    option_data["image_urls"] = option_images

                options.append(option_data)

                # Extract explanation and remarks with any image URLs
                explanation, explanation_images = extract_image_urls(
                    row.get("Explanation", "")
                )
                remarks, remarks_images = extract_image_urls(row.get("Remarks", ""))

                # Create question object
                question = Question(
                    title=question_text[:50]
                    + ("..." if len(question_text) > 50 else ""),
                    question_text=question_text,
                    question_type=QuestionType.MCQ,
                    difficulty_level=difficulty_enum,
                    exam_type=exam_subcategory,
                    options=options,
                    explanation=explanation,
                    subject=subject,
                    topic=topic or "General",
                    created_by=str(current_user.id),
                    tags=[exam_category_enum.value, exam_subcategory, subject],
                    is_active=True,
                )

                # Add image URLs to question metadata
                question_metadata = {}
                if question_images:
                    question_metadata["question_images"] = question_images
                if explanation_images:
                    question_metadata["explanation_images"] = explanation_images
                if remarks_images:
                    question_metadata["remarks_images"] = remarks_images
                if remarks:
                    question_metadata["remarks"] = remarks

                # Store metadata if any
                # if question_metadata:
                # You might need to add a metadata field to your Question model
                # This is just a suggestion for where to store additional info
                # question.metadata = question_metadata

                # Insert question into database
                await question.insert()
                questions.append(question)

            except Exception as e:
                errors.append(f"Error processing question at row {idx+1}: {str(e)}")

        # Handle test series creation or update
        test_series = None
        if existing_test_id:
            # Update existing test
            test_series = await TestSeries.get(existing_test_id)
            if not test_series:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Test with ID {existing_test_id} not found",
                )

            # Add new questions to existing test
            question_ids = [str(q.id) for q in questions]
            test_series.question_ids.extend(question_ids)
            test_series.total_questions = len(test_series.question_ids)
            await test_series.save()
        else:
            # Create new test series
            test_series = TestSeries(
                title=test_title,
                description=f"{test_title} for {exam_subcategory}",
                exam_category=exam_category_enum.value,
                exam_subcategory=exam_subcategory,
                subject=subject,
                total_questions=len(questions),
                duration_minutes=duration_minutes,
                max_score=len(questions),  # 1 point per question
                difficulty=test_difficulty_enum,
                question_ids=[str(q.id) for q in questions],
                is_free=is_free_bool,
                created_by=str(current_user.id),
            )
            await test_series.insert()

        # Log admin action
        admin_action = AdminAction(
            admin_id=str(current_user.id),
            action_type=(
                ActionType.CREATE if not existing_test_id else ActionType.UPDATE
            ),
            target_collection="test_series",
            target_id=str(test_series.id),
            changes={
                "action": "import_questions",
                "questions_added": len(questions),
                "source": file.filename,
            },
        )
        await admin_action.insert()

        return {
            "message": f"Successfully imported {len(questions)} questions",
            "test_id": str(test_series.id),
            "test_title": test_series.title,
            "questions_imported": len(questions),
            "errors": errors if errors else None,
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import questions: {str(e)}",
        )


# Also add an endpoint to view test details including questions
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
        # Get test
        test = await TestSeries.get(test_id)
        if not test:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Test not found"
            )

        # Get questions
        questions = []
        if test.question_ids:
            questions = await Question.find(
                {"_id": {"$in": test.question_ids}}
            ).to_list()

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

        return {
            "message": "Test questions retrieved successfully",
            "test": {
                "id": str(test.id),
                "title": test.title,
                "exam_category": test.exam_category,
                "exam_subcategory": test.exam_subcategory,
                "total_questions": test.total_questions,
                "duration_minutes": test.duration_minutes,
            },
            "questions": question_data,
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve test questions: {str(e)}",
        )


@router.post(
    "/create-admin",
    response_model=Dict[str, Any],
    summary="Create admin account",
    description="Admin endpoint to create another admin account",
)
async def create_admin(
    admin_data: UserRegisterRequest,
    current_user: User = Depends(
        admin_required
    ),  # Ensures only admins can create admins
):
    """Create a new admin account (Admin only)"""
    try:

        # Create admin user
        hashed_password = AuthService.get_password_hash(admin_data.password)
        new_admin = User(
            name=admin_data.name,
            email=admin_data.email,
            phone=admin_data.phone,
            password_hash=hashed_password,
            role=UserRole.ADMIN,  # Set role as ADMIN
            is_active=True,
            is_verified=True,  # Auto-verify admin accounts
        )
        await new_admin.insert()

        # Log the admin creation
        admin_action = AdminAction(
            admin_id=str(current_user.id),
            action_type=ActionType.CREATE,
            target_collection="users",
            target_id=str(new_admin.id),
            changes={"action": "admin_created"},
        )
        await admin_action.insert()

        return {"message": "Admin created successfully", "admin_id": str(new_admin.id)}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create admin: {str(e)}",
        )
