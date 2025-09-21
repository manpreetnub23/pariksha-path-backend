# from datetime import datetime, timezone
# import io
# import re
# import pandas as pd
# from typing import List, Optional, Dict, Any

# from fastapi import (
#     APIRouter,
#     HTTPException,
#     Depends,
#     status,
#     Query,
#     UploadFile,
#     File,
#     Form,
#     Request,
# )
# from pydantic import BaseModel, EmailStr
# from pydantic import Field
# from ..models.test import TestSeries, TestDifficulty
# from ..models.question import (
#     Question,
#     QuestionType,
#     DifficultyLevel,
#     QuestionOption,
#     ImageAttachment,
# )
# from ..models.admin_action import AdminAction, ActionType
# from ..models.user import User
# from ..models.enums import UserRole, ExamCategory
# from ..models.user_analytics import UserAnalytics
# from ..auth import AuthService, UserRegisterRequest
# from ..dependencies import admin_required, get_current_user

# router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


# # Student Management Request/Response Models
# class StudentUpdateRequest(BaseModel):
#     name: Optional[str] = None
#     phone: Optional[str] = None
#     is_active: Optional[bool] = None
#     preferred_exam_categories: Optional[List[ExamCategory]] = None
#     is_verified: Optional[bool] = None


# class StudentResponse(BaseModel):
#     id: str
#     name: str
#     email: EmailStr
#     phone: str
#     role: str
#     is_active: bool
#     is_verified: bool
#     is_email_verified: bool
#     preferred_exam_categories: List[str]
#     enrolled_courses: List[str]
#     created_at: datetime
#     last_login: Optional[datetime] = None


# class StudentFilterParams(BaseModel):
#     search: Optional[str] = None
#     exam_category: Optional[ExamCategory] = None
#     is_active: Optional[bool] = None
#     is_verified: Optional[bool] = None
#     sort_by: Optional[str] = "created_at"
#     sort_order: Optional[str] = "desc"


# class PasswordResetRequest(BaseModel):
#     new_password: str


# # Request/Response Models for Questions
# class ImageAttachmentRequest(BaseModel):
#     url: str
#     alt_text: Optional[str] = None
#     caption: Optional[str] = None
#     order: int = 0
#     file_size: Optional[int] = None
#     dimensions: Optional[Dict[str, int]] = Field(default_factory=dict)


# class OptionModel(BaseModel):
#     text: str
#     is_correct: bool
#     images: List[ImageAttachmentRequest] = Field(default_factory=list)
#     order: int = 0


# class QuestionCreateRequest(BaseModel):
#     title: str
#     question_text: str
#     question_type: QuestionType
#     difficulty_level: DifficultyLevel
#     exam_type: str
#     exam_year: Optional[int] = None
#     options: List[OptionModel]
#     explanation: Optional[str] = None
#     explanation_images: List[ImageAttachmentRequest] = Field(default_factory=list)
#     remarks: Optional[str] = None
#     remarks_images: List[ImageAttachmentRequest] = Field(default_factory=list)
#     question_images: List[ImageAttachmentRequest] = Field(default_factory=list)
#     subject: str
#     topic: str
#     tags: List[str] = Field(default_factory=list)

#     class Config:
#         json_schema_extra = {
#             "example": {
#                 "title": "Newton's First Law",
#                 "question_text": "What is Newton's First Law of Motion?",
#                 "question_type": "mcq",
#                 "difficulty_level": "medium",
#                 "exam_type": "JEE Main",
#                 "exam_year": 2023,
#                 "options": [
#                     {
#                         "text": "An object at rest stays at rest unless acted upon by an external force.",
#                         "is_correct": True,
#                     },
#                     {
#                         "text": "Force equals mass times acceleration.",
#                         "is_correct": False,
#                     },
#                     {
#                         "text": "For every action, there is an equal and opposite reaction.",
#                         "is_correct": False,
#                     },
#                     {
#                         "text": "Energy can neither be created nor destroyed.",
#                         "is_correct": False,
#                     },
#                 ],
#                 "explanation": "Newton's First Law states that an object will remain at rest or in uniform motion in a straight line unless acted upon by an external force.",
#                 "subject": "Physics",
#                 "topic": "Mechanics",
#                 "tags": ["newton", "motion", "laws"],
#             }
#         }


# class QuestionUpdateRequest(BaseModel):
#     title: Optional[str] = None
#     question_text: Optional[str] = None
#     question_type: Optional[QuestionType] = None
#     difficulty_level: Optional[DifficultyLevel] = None
#     exam_year: Optional[int] = None
#     options: Optional[List[OptionModel]] = None
#     explanation: Optional[str] = None
#     explanation_images: Optional[List[ImageAttachmentRequest]] = Field(default=None)
#     remarks: Optional[str] = None
#     remarks_images: Optional[List[ImageAttachmentRequest]] = Field(default=None)
#     question_images: Optional[List[ImageAttachmentRequest]] = Field(default=None)
#     subject: Optional[str] = None
#     topic: Optional[str] = None
#     tags: Optional[List[str]] = Field(default=None)
#     is_active: Optional[bool] = None


# class QuestionResponse(BaseModel):
#     id: str
#     title: str
#     question_text: str
#     question_type: str
#     difficulty_level: str
#     exam_year: Optional[int]
#     options: List[Dict[str, Any]]
#     explanation: Optional[str]
#     explanation_images: List[Dict[str, Any]]
#     remarks: Optional[str]
#     remarks_images: List[Dict[str, Any]]
#     question_images: List[Dict[str, Any]]
#     subject: str
#     topic: str
#     tags: List[str]
#     is_active: bool
#     created_by: str
#     created_at: datetime
#     updated_at: datetime


# # Helper function to extract image URLs from text
# def extract_image_urls(text):
#     if not isinstance(text, str):
#         return text, []

#     # Pattern to match URLs
#     url_pattern = r"https?://\S+"
#     urls = re.findall(url_pattern, text)

#     # Remove URLs from text
#     clean_text = re.sub(url_pattern, "", text).strip()

#     return clean_text, urls


# # Student Management Routes


# @router.get(
#     "/students",
#     response_model=Dict[str, Any],
#     summary="List all students",
#     description="Admin endpoint to list all students with filters and pagination",
# )
# async def list_students(
#     search: Optional[str] = Query(None, description="Search by name or email"),
#     exam_category: Optional[ExamCategory] = Query(
#         None, description="Filter by exam category"
#     ),
#     is_active: Optional[bool] = Query(None, description="Filter by active status"),
#     is_verified: Optional[bool] = Query(
#         None, description="Filter by verification status"
#     ),
#     sort_by: str = Query("created_at", description="Field to sort by"),
#     sort_order: str = Query("desc", description="Sort order (asc or desc)"),
#     page: int = Query(1, description="Page number", ge=1),
#     limit: int = Query(10, description="Items per page", ge=1, le=100),
#     current_user: User = Depends(admin_required),
# ):
#     """List all students with filters and pagination (Admin only)"""
#     try:
#         # Build query filters
#         query_filters = {"role": UserRole.STUDENT}

#         if search:
#             # Search in name or email
#             query_filters["$or"] = [
#                 {"name": {"$regex": search, "$options": "i"}},
#                 {"email": {"$regex": search, "$options": "i"}},
#             ]

#         if exam_category:
#             query_filters["preferred_exam_categories"] = exam_category

#         if is_active is not None:
#             query_filters["is_active"] = is_active

#         if is_verified is not None:
#             query_filters["is_verified"] = is_verified

#         # Calculate pagination
#         skip = (page - 1) * limit

#         # Set sort order
#         sort_direction = -1 if sort_order == "desc" else 1

#         # Fetch users
#         students = (
#             await User.find(query_filters)
#             .sort([(sort_by, sort_direction)])
#             .skip(skip)
#             .limit(limit)
#             .to_list()
#         )

#         # Count total matching users for pagination info
#         total_students = await User.find(query_filters).count()
#         total_pages = (total_students + limit - 1) // limit

#         # Convert user objects to response format
#         student_responses = [
#             StudentResponse(
#                 id=str(student.id),
#                 name=student.name,
#                 email=student.email,
#                 phone=student.phone,
#                 role=student.role.value,
#                 is_active=student.is_active,
#                 is_verified=student.is_verified,
#                 is_email_verified=student.is_email_verified,
#                 preferred_exam_categories=[
#                     cat.value for cat in student.preferred_exam_categories
#                 ],
#                 enrolled_courses=student.enrolled_courses,
#                 created_at=student.created_at,
#                 last_login=student.last_login,
#             )
#             for student in students
#         ]

#         # Log admin action
#         admin_action = AdminAction(
#             admin_id=str(current_user.id),
#             action_type=ActionType.CREATE,
#             target_collection="users",
#             target_id="N/A",
#             changes={"action": "list_students", "filters": str(query_filters)},
#         )
#         await admin_action.insert()

#         return {
#             "message": "Students retrieved successfully",
#             "data": student_responses,
#             "pagination": {
#                 "total": total_students,
#                 "page": page,
#                 "limit": limit,
#                 "total_pages": total_pages,
#             },
#         }

#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to retrieve students: {str(e)}",
#         )


# @router.get(
#     "/students/{student_id}",
#     response_model=Dict[str, Any],
#     summary="Get student details",
#     description="Admin endpoint to get detailed information about a specific student",
# )
# async def get_student(
#     student_id: str,
#     current_user: User = Depends(admin_required),
# ):
#     """Get detailed information about a specific student (Admin only)"""
#     try:
#         # Find the student by ID
#         student = await User.get(student_id)
#         if not student:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="Student not found",
#             )

#         # Check if the user is actually a student
#         if student.role != UserRole.STUDENT:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="User is not a student",
#             )

#         # Convert to response model
#         student_response = StudentResponse(
#             id=str(student.id),
#             name=student.name,
#             email=student.email,
#             phone=student.phone,
#             role=student.role.value,
#             is_active=student.is_active,
#             is_verified=student.is_verified,
#             is_email_verified=student.is_email_verified,
#             preferred_exam_categories=[
#                 cat.value for cat in student.preferred_exam_categories
#             ],
#             enrolled_courses=student.enrolled_courses,
#             created_at=student.created_at,
#             last_login=student.last_login,
#         )

#         # Get additional details about purchases, test attempts, etc.
#         additional_info = {
#             "purchased_test_series": student.purchased_test_series,
#             "purchased_materials": student.purchased_materials,
#             "has_premium_access": student.has_premium_access,
#             "completed_tests": len(student.completed_tests),
#             "dashboard_settings": student.dashboard_settings,
#         }

#         # Log admin action
#         admin_action = AdminAction(
#             admin_id=str(current_user.id),
#             action_type=ActionType.CREATE,
#             target_collection="users",
#             target_id=student_id,
#             changes={"action": "get_student_details"},
#         )
#         await admin_action.insert()

#         return {
#             "message": "Student details retrieved successfully",
#             "student": student_response,
#             "additional_info": additional_info,
#         }

#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to retrieve student details: {str(e)}",
#         )


# @router.put(
#     "/students/{student_id}",
#     response_model=Dict[str, Any],
#     summary="Update student information",
#     description="Admin endpoint to update a student's profile information",
# )
# async def update_student(
#     student_id: str,
#     update_data: StudentUpdateRequest,
#     current_user: User = Depends(admin_required),
# ):
#     """Update a student's profile information (Admin only)"""
#     try:
#         # Find the student
#         student = await User.get(student_id)
#         if not student:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="Student not found",
#             )

#         # Check if the user is actually a student
#         if student.role != UserRole.STUDENT:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="User is not a student",
#             )

#         # Track changes for audit log
#         changes = {}

#         # Update fields if provided
#         update_dict = update_data.dict(exclude_unset=True)

#         for field, value in update_dict.items():
#             if value is not None:
#                 # Special validation for phone if provided
#                 if field == "phone" and value != student.phone:
#                     # Check if phone already exists for another user
#                     existing_phone = await User.find_one(
#                         {"phone": value, "_id": {"$ne": student.id}}
#                     )
#                     if existing_phone:
#                         raise HTTPException(
#                             status_code=status.HTTP_400_BAD_REQUEST,
#                             detail="Phone number already exists",
#                         )

#                 # Set the new value
#                 setattr(student, field, value)
#                 changes[field] = str(value)

#         # Only update if there are changes
#         if changes:
#             student.update_timestamp()
#             await student.save()

#             # Log admin action
#             admin_action = AdminAction(
#                 admin_id=str(current_user.id),
#                 action_type=ActionType.UPDATE,
#                 target_collection="users",
#                 target_id=student_id,
#                 changes=changes,
#             )
#             await admin_action.insert()

#             # Create response
#             student_response = StudentResponse(
#                 id=str(student.id),
#                 name=student.name,
#                 email=student.email,
#                 phone=student.phone,
#                 role=student.role.value,
#                 is_active=student.is_active,
#                 is_verified=student.is_verified,
#                 is_email_verified=student.is_email_verified,
#                 preferred_exam_categories=[
#                     cat.value for cat in student.preferred_exam_categories
#                 ],
#                 enrolled_courses=student.enrolled_courses,
#                 created_at=student.created_at,
#                 last_login=student.last_login,
#             )

#             return {
#                 "message": "Student updated successfully",
#                 "student": student_response,
#                 "changes": changes,
#             }
#         else:
#             return {
#                 "message": "No changes to apply",
#                 "student_id": student_id,
#             }

#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to update student: {str(e)}",
#         )


# @router.delete(
#     "/students/{student_id}",
#     response_model=Dict[str, Any],
#     summary="Deactivate student",
#     description="Admin endpoint to deactivate a student (soft delete)",
# )
# async def deactivate_student(
#     student_id: str,
#     current_user: User = Depends(admin_required),
# ):
#     """Deactivate a student (Admin only)"""
#     try:
#         # Find the student
#         student = await User.get(student_id)
#         if not student:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="Student not found",
#             )

#         # Check if the user is actually a student
#         if student.role != UserRole.STUDENT:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="User is not a student",
#             )

#         # Check if student is already inactive
#         if not student.is_active:
#             return {
#                 "message": "Student is already deactivated",
#                 "student_id": student_id,
#             }

#         # Soft delete by setting is_active=False
#         student.is_active = False
#         student.update_timestamp()
#         await student.save()

#         # Log admin action
#         admin_action = AdminAction(
#             admin_id=str(current_user.id),
#             action_type=ActionType.DELETE,
#             target_collection="users",
#             target_id=student_id,
#             changes={"is_active": False},
#         )
#         await admin_action.insert()

#         return {
#             "message": "Student deactivated successfully",
#             "student_id": student_id,
#         }

#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to deactivate student: {str(e)}",
#         )


# @router.post(
#     "/students/{student_id}/reset-password",
#     response_model=Dict[str, Any],
#     summary="Reset student password",
#     description="Admin endpoint to reset a student's password",
# )
# async def reset_student_password(
#     student_id: str,
#     password_data: PasswordResetRequest,
#     current_user: User = Depends(admin_required),
# ):
#     """Reset a student's password (Admin only)"""
#     try:
#         # Find the student
#         student = await User.get(student_id)
#         if not student:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="Student not found",
#             )

#         # Check if the user is actually a student
#         if student.role != UserRole.STUDENT:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="User is not a student",
#             )

#         # Validate new password
#         if not AuthService.validate_password(password_data.new_password):
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Password must be at least 8 characters long and contain uppercase, lowercase, number, and special character",
#             )

#         # Update password
#         student.password_hash = AuthService.get_password_hash(
#             password_data.new_password
#         )
#         student.update_timestamp()
#         await student.save()

#         # Log admin action
#         admin_action = AdminAction(
#             admin_id=str(current_user.id),
#             action_type=ActionType.UPDATE,
#             target_collection="users",
#             target_id=student_id,
#             changes={"action": "password_reset"},
#         )
#         await admin_action.insert()

#         return {
#             "message": "Student password reset successfully",
#             "student_id": student_id,
#         }

#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to reset student password: {str(e)}",
#         )


# @router.get(
#     "/students/{student_id}/analytics",
#     response_model=Dict[str, Any],
#     summary="Get student analytics",
#     description="Admin endpoint to view a student's performance analytics",
# )
# async def get_student_analytics(
#     student_id: str,
#     current_user: User = Depends(admin_required),
# ):
#     """Get a student's performance analytics (Admin only)"""
#     try:
#         # Find the student
#         student = await User.get(student_id)
#         if not student:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="Student not found",
#             )

#         # Check if the user is actually a student
#         if student.role != UserRole.STUDENT:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="User is not a student",
#             )

#         # Get analytics data from UserAnalytics collection
#         analytics = await UserAnalytics.find_one({"user_id": student_id})

#         if not analytics:
#             # Create a new analytics record if none exists
#             analytics = UserAnalytics(user_id=student_id)
#             await analytics.insert()

#         # Basic student info
#         student_info = {
#             "id": str(student.id),
#             "name": student.name,
#             "email": student.email,
#             "preferred_exam_categories": [
#                 cat.value for cat in student.preferred_exam_categories
#             ],
#         }

#         # Format analytics data
#         analytics_data = {
#             # Test performance
#             "tests_taken": analytics.tests_taken,
#             "tests_passed": analytics.tests_passed,
#             "avg_accuracy": analytics.avg_accuracy,
#             "avg_test_score": analytics.avg_test_score,
#             "avg_percentile": analytics.avg_percentile,
#             "best_percentile": analytics.best_percentile,
#             # Subject performance
#             "subject_performance": analytics.subject_performance,
#             "strongest_subjects": analytics.strongest_subjects,
#             "weakest_subjects": analytics.weakest_subjects,
#             # Time and engagement
#             "total_study_time_minutes": analytics.total_study_time_minutes,
#             "study_habits": analytics.study_habits.dict(),
#             "materials_accessed": analytics.materials_accessed,
#             "materials_completed": analytics.materials_completed,
#             # Detailed breakdowns
#             "difficulty_performance": analytics.difficulty_performance,
#             "exam_readiness": analytics.exam_readiness,
#             # Last update time
#             "last_updated": analytics.last_updated,
#         }

#         # Log admin action
#         admin_action = AdminAction(
#             admin_id=str(current_user.id),
#             action_type=ActionType.CREATE,
#             target_collection="user_analytics",
#             target_id=student_id,
#             changes={"action": "view_analytics"},
#         )
#         await admin_action.insert()

#         return {
#             "message": "Student analytics retrieved successfully",
#             "student": student_info,
#             "analytics": analytics_data,
#         }

#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to retrieve student analytics: {str(e)}",
#         )


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

#     def normalize_enum(value: str, enum_cls):
#         for member in enum_cls:
#             if value.lower() == member.value.lower():
#                 return member
#         raise HTTPException(
#             status_code=400,
#             detail=f"Invalid {enum_cls.__name__}: {value}. "
#             f"Allowed: {[m.value for m in enum_cls]}",
#         )

#     # Normalize raw inputs
#     raw_exam_category = exam_category.strip()
#     raw_difficulty = difficulty.strip()
#     raw_is_free = is_free.strip().lower()

#     # Convert to enum types
#     exam_category_enum = normalize_enum(raw_exam_category, ExamCategory)
#     difficulty_enum = normalize_enum(raw_difficulty, DifficultyLevel)
#     test_difficulty_enum = normalize_enum(raw_difficulty, TestDifficulty)
#     is_free_bool = raw_is_free in ("true", "1", "yes", "on")

#     """
#     Import questions from CSV file and create/update a test.

#     The CSV should have the following columns:
#     - Question
#     - Option A
#     - Option B
#     - Option C
#     - Option D
#     - Correct Answer (A, B, C, or D)
#     - Explanation (optional)
#     - Remarks (optional)

#     Images can be included as URLs in any field.
#     """
#     print("\n=== Starting import_questions_from_csv ===")

#     # For now, return a success response since the actual CSV processing is commented out

#     try:
#         # Check if file is provided
#         if not file:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST, detail="No file provided"
#             )
#         else:
#             print(f"File provided: {file.filename} (type: {type(file.filename)})")
#         # Read and validate file content
#         try:
#             contents = await file.read()
#             if not contents:
#                 raise HTTPException(
#                     status_code=status.HTTP_400_BAD_REQUEST,
#                     detail="Empty file provided",
#                 )

#             print(
#                 f"\n=== First 200 chars of file ===\n{contents[:200].decode('utf-8', errors='replace')}..."
#             )

#             # Try to read CSV with different encodings if needed
#             try:
#                 df = pd.read_csv(io.BytesIO(contents))
#             except Exception as e:
#                 print(f"Error reading CSV with default encoding: {str(e)}")
#                 # Try with different encodings
#                 for encoding in ["utf-8", "latin1", "iso-8859-1", "cp1252"]:
#                     try:
#                         df = pd.read_csv(io.BytesIO(contents), encoding=encoding)
#                         print(f"Successfully read CSV with {encoding} encoding")
#                         break
#                     except:
#                         continue
#                 else:
#                     raise HTTPException(
#                         status_code=status.HTTP_400_BAD_REQUEST,
#                         detail="Could not read CSV file with any standard encoding",
#                     )

#             print("\n=== CSV Headers ===")
#             print(df.columns.tolist())
#             print("\n=== First row ===")
#             print(df.iloc[0].to_dict() if not df.empty else "Empty DataFrame")

#         except Exception as e:
#             print(f"Error processing file: {str(e)}")
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail=f"Error processing file: {str(e)}",
#             )

#         # Validate CSV structure
#         required_columns = [
#             "Question",
#             "Option A",
#             "Option B",
#             "Option C",
#             "Option D",
#             "Correct Answer",
#         ]
#         print("Validated")
#         for col in required_columns:
#             if col not in df.columns:
#                 raise HTTPException(
#                     status_code=status.HTTP_400_BAD_REQUEST,
#                     detail=f"Missing required column: {col}",
#                 )

#         # Process questions
#         questions = []
#         errors = []

#         for idx, row in df.iterrows():
#             try:
#                 print("Start")
#                 print(idx, row)
#                 # Extract image URLs from question text
#                 question_text, question_images = extract_image_urls(row["Question"])

#                 # Convert question images to ImageAttachment objects
#                 question_image_attachments = []
#                 for i, img_url in enumerate(question_images):
#                     question_image_attachments.append(
#                         ImageAttachment(
#                             url=img_url, alt_text=f"Question image {i+1}", order=i
#                         )
#                     )

#                 # Process options and extract image URLs
#                 options = []
#                 for i, opt in enumerate(["A", "B", "C", "D"]):
#                     option_text, option_images = extract_image_urls(
#                         row[f"Option {opt}"]
#                     )
#                     is_correct = str(row["Correct Answer"]).strip().upper() == opt

#                     # Convert option images to ImageAttachment objects
#                     option_image_attachments = []
#                     for j, img_url in enumerate(option_images):
#                         option_image_attachments.append(
#                             ImageAttachment(
#                                 url=img_url,
#                                 alt_text=f"Option {opt} image {j+1}",
#                                 order=j,
#                             )
#                         )

#                     options.append(
#                         QuestionOption(
#                             text=option_text,
#                             is_correct=is_correct,
#                             images=option_image_attachments,
#                             order=i,
#                         )
#                     )

#                 # Extract explanation and remarks with any image URLs
#                 explanation, explanation_images = extract_image_urls(
#                     row.get("Explanation", "")
#                 )
#                 remarks, remarks_images = extract_image_urls(row.get("Remarks", ""))

#                 # Convert explanation images to ImageAttachment objects
#                 explanation_image_attachments = []
#                 for i, img_url in enumerate(explanation_images):
#                     explanation_image_attachments.append(
#                         ImageAttachment(
#                             url=img_url, alt_text=f"Explanation image {i+1}", order=i
#                         )
#                     )

#                 # Convert remarks images to ImageAttachment objects
#                 remarks_image_attachments = []
#                 for i, img_url in enumerate(remarks_images):
#                     remarks_image_attachments.append(
#                         ImageAttachment(
#                             url=img_url, alt_text=f"Remarks image {i+1}", order=i
#                         )
#                     )

#                 # Create question object
#                 question = Question(
#                     title=question_text[:50]
#                     + ("..." if len(question_text) > 50 else ""),
#                     question_text=question_text,
#                     question_type=QuestionType.MCQ,
#                     difficulty_level=difficulty_enum,
#                     exam_type=exam_subcategory,
#                     options=options,
#                     explanation=explanation,
#                     explanation_images=explanation_image_attachments,
#                     remarks=remarks,
#                     remarks_images=remarks_image_attachments,
#                     question_images=question_image_attachments,
#                     subject=subject,
#                     topic=topic or "General",
#                     created_by=str(current_user.id),
#                     tags=[exam_category_enum.value, exam_subcategory, subject],
#                     is_active=True,
#                 )

#                 # Insert question into database
#                 await question.insert()
#                 questions.append(question)

#             except Exception as e:
#                 errors.append(f"Error processing question at row {idx+1}: {str(e)}")

#         # Handle test series creation or update
#         test_series = None
#         if existing_test_id:
#             # Update existing test
#             test_series = await TestSeries.get(existing_test_id)
#             if not test_series:
#                 raise HTTPException(
#                     status_code=status.HTTP_404_NOT_FOUND,
#                     detail=f"Test with ID {existing_test_id} not found",
#                 )

#             # Add new questions to existing test
#             question_ids = [str(q.id) for q in questions]
#             test_series.question_ids.extend(question_ids)
#             test_series.total_questions = len(test_series.question_ids)
#             await test_series.save()
#         else:
#             # Create new test series
#             test_series = TestSeries(
#                 title=test_title,
#                 description=f"{test_title} for {exam_subcategory}",
#                 exam_category=exam_category_enum.value,
#                 exam_subcategory=exam_subcategory,
#                 subject=subject,
#                 total_questions=len(questions),
#                 duration_minutes=duration_minutes,
#                 max_score=len(questions),  # 1 point per question
#                 difficulty=test_difficulty_enum,
#                 question_ids=[str(q.id) for q in questions],
#                 is_free=is_free_bool,
#                 created_by=str(current_user.id),
#             )
#             await test_series.insert()

#         # Log admin action
#         admin_action = AdminAction(
#             admin_id=str(current_user.id),
#             action_type=(
#                 ActionType.CREATE if not existing_test_id else ActionType.UPDATE
#             ),
#             target_collection="test_series",
#             target_id=str(test_series.id),
#             changes={
#                 "action": "import_questions",
#                 "questions_added": len(questions),
#                 "source": file.filename,
#             },
#         )
#         await admin_action.insert()

#         return {
#             "message": f"Successfully imported {len(questions)} questions",
#             "test_id": str(test_series.id),
#             "test_title": test_series.title,
#             "questions_imported": len(questions),
#             "errors": errors if errors else None,
#         }

#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to import questions: {str(e)}",
#         )


# # Also add an endpoint to view test details including questions
# @router.get(
#     "/tests/{test_id}/questions",
#     response_model=Dict[str, Any],
#     summary="Get test questions",
#     description="Admin endpoint to view all questions in a test",
# )
# async def get_test_questions(
#     test_id: str, current_user: User = Depends(admin_required)
# ):
#     """Get all questions for a specific test"""
#     try:
#         # Get test
#         test = await TestSeries.get(test_id)
#         if not test:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND, detail="Test not found"
#             )

#         # Get questions
#         questions = []
#         if test.question_ids:
#             questions = await Question.find(
#                 {"_id": {"$in": test.question_ids}}
#             ).to_list()

#         # Format response
#         question_data = [
#             {
#                 "id": str(q.id),
#                 "title": q.title,
#                 "question_text": q.question_text,
#                 "options": q.options,
#                 "explanation": q.explanation,
#                 "subject": q.subject,
#                 "topic": q.topic,
#                 "difficulty_level": q.difficulty_level,
#                 "metadata": getattr(q, "metadata", None),
#             }
#             for q in questions
#         ]

#         return {
#             "message": "Test questions retrieved successfully",
#             "test": {
#                 "id": str(test.id),
#                 "title": test.title,
#                 "exam_category": test.exam_category,
#                 "exam_subcategory": test.exam_subcategory,
#                 "total_questions": test.total_questions,
#                 "duration_minutes": test.duration_minutes,
#             },
#             "questions": question_data,
#         }

#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to retrieve test questions: {str(e)}",
#         )


# @router.put(
#     "/questions/{question_id}",
#     response_model=Dict[str, Any],
#     summary="Update question",
#     description="Admin endpoint to update a question",
# )
# async def update_question(
#     question_id: str,
#     question_data: QuestionUpdateRequest,
#     current_user: User = Depends(admin_required),
# ):
#     """Update a question (Admin only)"""
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
#         update_dict = question_data.dict(exclude_unset=True)
#         print(f"Update data received: {update_dict}")  # Debug log

#         # Detailed debug of image fields
#         print("========== DETAILED REQUEST DATA ==========")
#         if "question_images" in update_dict:
#             print(f"Question images in request: {update_dict['question_images']}")
#             print(f"Question images type: {type(update_dict['question_images'])}")
#             print(f"Question images length: {len(update_dict['question_images'])}")
#             if update_dict["question_images"]:
#                 print(f"First image in request: {update_dict['question_images'][0]}")
#         else:
#             print("No question_images field in request")

#         if "explanation_images" in update_dict:
#             print(f"Explanation images in request: {update_dict['explanation_images']}")
#             print(
#                 f"Explanation images length: {len(update_dict['explanation_images'])}"
#             )

#         if "options" in update_dict:
#             print(f"Options in request: {len(update_dict['options'])} options")
#             for i, opt in enumerate(update_dict["options"]):
#                 if "images" in opt and opt["images"]:
#                     print(f"Option {i+1} has {len(opt['images'])} images")
#                     print(f"First image: {opt['images'][0]}")
#         print("============================================")

#         for field, value in update_dict.items():
#             if value is not None:
#                 # Special handling for options to ensure correct format
#                 if field == "options" and isinstance(value, list):
#                     # Convert to QuestionOption objects
#                     question_options = []
#                     for i, option_data in enumerate(value):
#                         if (
#                             not isinstance(option_data, dict)
#                             or "text" not in option_data
#                             or "is_correct" not in option_data
#                         ):
#                             raise HTTPException(
#                                 status_code=status.HTTP_400_BAD_REQUEST,
#                                 detail="Invalid options format. Each option must have 'text' and 'is_correct' fields",
#                             )

#                         # Convert image attachments
#                         images = []
#                         for img_data in option_data.get("images", []):
#                             images.append(ImageAttachment(**img_data))

#                         question_options.append(
#                             QuestionOption(
#                                 text=option_data["text"],
#                                 is_correct=option_data["is_correct"],
#                                 images=images,
#                                 order=option_data.get("order", i),
#                             )
#                         )
#                     value = question_options

#                 # Special handling for image fields
#                 elif field in [
#                     "question_images",
#                     "explanation_images",
#                     "remarks_images",
#                 ] and isinstance(value, list):
#                     # Debug log for image data
#                     print(f"Processing {field} with {len(value)} items")
#                     for i, img in enumerate(value):
#                         print(f"Image {i+1} data: {img}")

#                     # Convert to ImageAttachment objects
#                     image_attachments = []
#                     for img_data in value:
#                         # Ensure all required fields are present
#                         if not img_data.get("url"):
#                             print(f"WARNING: Image missing URL: {img_data}")
#                             continue

#                         attachment = ImageAttachment(**img_data)
#                         image_attachments.append(attachment)
#                         print(f"Converted to ImageAttachment: {attachment}")

#                     print(f"Final {field} array: {image_attachments}")
#                     value = image_attachments

#                 # Handle field mapping for enum fields
#                 if field == "question_type" and isinstance(value, str):
#                     try:
#                         value = QuestionType(value)
#                     except ValueError:
#                         raise HTTPException(
#                             status_code=status.HTTP_400_BAD_REQUEST,
#                             detail=f"Invalid question_type: {value}. Must be one of {[t.value for t in QuestionType]}",
#                         )

#                 if field == "difficulty_level" and isinstance(value, str):
#                     try:
#                         value = DifficultyLevel(value)
#                     except ValueError:
#                         raise HTTPException(
#                             status_code=status.HTTP_400_BAD_REQUEST,
#                             detail=f"Invalid difficulty_level: {value}. Must be one of {[d.value for d in DifficultyLevel]}",
#                         )

#                 # Set the new value
#                 setattr(question, field, value)
#                 changes[field] = (
#                     str(value) if not isinstance(value, list) else "updated"
#                 )

#         # Only update if there are changes
#         if changes:
#             try:
#                 # Debug log before saving
#                 print("========== QUESTION BEFORE SAVE ==========")
#                 print(f"Question ID: {question_id}")
#                 print(f"Question images: {question.question_images}")
#                 if question.question_images:
#                     print(f"Number of question images: {len(question.question_images)}")
#                     for i, img in enumerate(question.question_images):
#                         print(f"Question image {i+1}: {img.dict()}")

#                 # Update timestamp and save
#                 question.update_timestamp()

#                 # Convert to dict to see what's being saved
#                 question_dict = question.dict()
#                 print("Question as dict before save:")
#                 print(
#                     f"question_images in dict: {question_dict.get('question_images')}"
#                 )

#                 # Save to database
#                 await question.save()

#                 # Verify the save worked by fetching the question again
#                 saved_question = await Question.get(question_id)
#                 print("========== QUESTION AFTER SAVE ==========")
#                 print(f"Saved question images: {saved_question.question_images}")
#                 if saved_question.question_images:
#                     print(
#                         f"Number of saved images: {len(saved_question.question_images)}"
#                     )
#                     for i, img in enumerate(saved_question.question_images):
#                         print(f"Saved image {i+1}: {img.dict()}")

#                 print(f"Question {question_id} updated successfully")  # Debug log

#                 # Log admin action
#                 admin_action = AdminAction(
#                     admin_id=str(current_user.id),
#                     action_type=ActionType.UPDATE,
#                     target_collection="questions",
#                     target_id=question_id,
#                     changes=changes,
#                 )
#                 await admin_action.insert()

#                 return {
#                     "message": "Question updated successfully",
#                     "question_id": question_id,
#                     "changes": changes,
#                 }
#             except Exception as save_error:
#                 print(f"Error saving question: {str(save_error)}")  # Debug log
#                 raise HTTPException(
#                     status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#                     detail=f"Failed to save question: {str(save_error)}",
#                 )
#         else:
#             return {
#                 "message": "No changes to apply",
#                 "question_id": question_id,
#             }

#     except HTTPException as e:
#         print(f"HTTP Exception in update_question: {str(e)}")  # Debug log
#         raise e
#     except Exception as e:
#         print(f"Unexpected error in update_question: {str(e)}")  # Debug log
#         import traceback

#         traceback.print_exc()  # Print full traceback
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to update question: {str(e)}",
#         )


# @router.get(
#     "/questions/{question_id}",
#     response_model=Dict[str, Any],
#     summary="Get question details",
#     description="Admin endpoint to get detailed information about a specific question",
# )
# async def get_question(
#     question_id: str,
#     current_user: User = Depends(admin_required),
# ):
#     """Get detailed information about a specific question (Admin only)"""
#     try:
#         # Find the question
#         question = await Question.get(question_id)
#         if not question:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="Question not found",
#             )

#         # Convert options to dict format
#         options_dict = []
#         for option in question.options:
#             option_dict = {
#                 "text": option.text,
#                 "is_correct": option.is_correct,
#                 "images": [img.dict() for img in option.images],
#                 "order": option.order,
#             }
#             options_dict.append(option_dict)

#         # Convert to response format
#         question_response = QuestionResponse(
#             id=str(question.id),
#             title=question.title,
#             question_text=question.question_text,
#             question_type=question.question_type.value,
#             difficulty_level=question.difficulty_level.value,
#             exam_year=question.exam_year,
#             options=options_dict,
#             explanation=question.explanation,
#             explanation_images=[img.dict() for img in question.explanation_images],
#             remarks=question.remarks,
#             remarks_images=[img.dict() for img in question.remarks_images],
#             question_images=[img.dict() for img in question.question_images],
#             subject=question.subject,
#             topic=question.topic,
#             tags=question.tags,
#             is_active=question.is_active,
#             created_by=question.created_by,
#             created_at=question.created_at,
#             updated_at=question.updated_at,
#         )

#         return {
#             "message": "Question details retrieved successfully",
#             "question": question_response,
#         }

#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to retrieve question details: {str(e)}",
#         )


# @router.delete(
#     "/questions/{question_id}",
#     response_model=Dict[str, Any],
#     summary="Delete question",
#     description="Admin endpoint to delete a question",
# )
# async def delete_question(
#     question_id: str,
#     current_user: User = Depends(admin_required),
# ):
#     """Delete a question (Admin only)"""
#     try:
#         # Find the question
#         question = await Question.get(question_id)
#         if not question:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="Question not found",
#             )

#         # Store question details for audit log
#         question_details = {
#             "title": question.title,
#             "question_text": question.question_text,
#             "subject": question.subject,
#             "topic": question.topic,
#             "section": question.section,
#         }

#         # Delete the question
#         await question.delete()

#         # Log admin action
#         admin_action = AdminAction(
#             admin_id=str(current_user.id),
#             action_type=ActionType.DELETE,
#             target_collection="questions",
#             target_id=question_id,
#             changes={"deleted_question": question_details},
#         )
#         await admin_action.insert()

#         return {
#             "message": "Question deleted successfully",
#             "question_id": question_id,
#             "deleted_question": question_details,
#         }

#     except HTTPException as e:
#         print(f"HTTP Exception in delete_question: {str(e)}")  # Debug log
#         raise e
#     except Exception as e:
#         print(f"Unexpected error in delete_question: {str(e)}")  # Debug log
#         import traceback

#         traceback.print_exc()  # Print full traceback
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to delete question: {str(e)}",
#         )


# @router.post(
#     "/create-admin",
#     response_model=Dict[str, Any],
#     summary="Create admin account",
#     description="Admin endpoint to create another admin account",
# )
# async def create_admin(
#     admin_data: UserRegisterRequest,
#     current_user: User = Depends(
#         admin_required
#     ),  # Ensures only admins can create admins
# ):
#     """Create a new admin account (Admin only)"""
#     try:

#         # Create admin user
#         hashed_password = AuthService.get_password_hash(admin_data.password)
#         new_admin = User(
#             name=admin_data.name,
#             email=admin_data.email,
#             phone=admin_data.phone,
#             password_hash=hashed_password,
#             role=UserRole.ADMIN,  # Set role as ADMIN
#             is_active=True,
#             is_verified=True,  # Auto-verify admin accounts
#         )
#         await new_admin.insert()

#         # Log the admin creation
#         admin_action = AdminAction(
#             admin_id=str(current_user.id),
#             action_type=ActionType.CREATE,
#             target_collection="users",
#             target_id=str(new_admin.id),
#             changes={"action": "admin_created"},
#         )
#         await admin_action.insert()

#         return {"message": "Admin created successfully", "admin_id": str(new_admin.id)}
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to create admin: {str(e)}",
#         )
