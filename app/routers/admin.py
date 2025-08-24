from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, status, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr
from ..models.question import Question, QuestionType, DifficultyLevel
from ..models.admin_action import AdminAction, ActionType
from ..models.user import User, UserRole, ExamCategory
from ..models.user_analytics import UserAnalytics
from ..auth import AuthService
from datetime import datetime, timezone

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])
security = HTTPBearer()


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


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """Get current user from JWT token"""
    return await AuthService.get_current_user(credentials.credentials)


# Admin-only middleware
async def admin_required(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


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
