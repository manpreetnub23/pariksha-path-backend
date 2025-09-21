# from datetime import datetime, timezone
# from fastapi import (
#     APIRouter,
#     HTTPException,
#     Depends,
#     status,
#     Query,
#     UploadFile,
#     File,
#     Form,
# )
# from typing import List, Optional, Dict, Any, Union
# from pydantic import BaseModel, Field
# import csv
# import io
# from datetime import datetime
# from bson import ObjectId

# from ..models.course import Course, ExamSubCategory, Section
# from ..models.question import (
#     Question,
#     QuestionType,
#     DifficultyLevel,
#     QuestionOption,
# )
# from ..models.admin_action import AdminAction, ActionType
# from ..models.user import User
# from ..models.enums import ExamCategory
# from ..dependencies import admin_required, get_current_user
# import re
# from fastapi import Body
# from app.config import settings

# router = APIRouter(prefix="/api/v1/courses", tags=["Courses"])


# # A course is an exam for all intents and purposes.


# # Request/Response Models
# class CourseCreateRequest(BaseModel):
#     title: str
#     code: str
#     category: ExamCategory
#     sub_category: str
#     description: str
#     price: float
#     is_free: bool = False
#     discount_percent: Optional[float] = None
#     material_ids: List[str] = []
#     test_series_ids: List[str] = []
#     thumbnail_url: str
#     icon_url: Optional[str] = None
#     priority_order: int = 0
#     banner_url: Optional[str] = None
#     tagline: Optional[str] = None
#     sections: List[str] = []

#     class Config:
#         json_schema_extra = {
#             "example": {
#                 "title": "Complete JEE Main Physics",
#                 "code": "JEE-PHY-001",
#                 "category": "engineering",
#                 "sub_category": "JEE Main",
#                 "description": "Comprehensive course for JEE Main Physics preparation",
#                 "price": 4999.0,
#                 "is_free": False,
#                 "discount_percent": 10.0,
#                 "material_ids": [],
#                 "test_series_ids": [],
#                 "thumbnail_url": "https://example.com/images/jee-physics.jpg",
#                 "icon_url": "https://example.com/icons/physics.png",
#                 "priority_order": 1,
#                 "banner_url": "https://example.com/banners/jee-physics-banner.jpg",
#                 "tagline": "Master Physics concepts for JEE Main",
#                 "sections": ["Physics", "Chemistry", "Biology"],
#             }
#         }


# class CourseUpdateRequest(BaseModel):
#     title: Optional[str] = None
#     description: Optional[str] = None
#     sections: Optional[List[str]] = None
#     price: Optional[float] = None
#     is_free: Optional[bool] = None
#     discount_percent: Optional[float] = None
#     material_ids: Optional[List[str]] = None
#     test_series_ids: Optional[List[str]] = None
#     thumbnail_url: Optional[str] = None
#     icon_url: Optional[str] = None
#     priority_order: Optional[int] = None
#     banner_url: Optional[str] = None
#     tagline: Optional[str] = None
#     is_active: Optional[bool] = None


# class CourseResponse(BaseModel):
#     id: str
#     title: str
#     code: str
#     category: str
#     sub_category: str
#     description: str
#     sections: Optional[List[str]] = None
#     price: float
#     is_free: bool
#     discount_percent: Optional[float] = None
#     material_ids: List[str]
#     test_series_ids: List[str]
#     enrolled_students_count: int
#     thumbnail_url: str
#     icon_url: Optional[str] = None
#     banner_url: Optional[str] = None
#     tagline: Optional[str] = None
#     is_active: bool
#     created_at: datetime
#     updated_at: datetime


# # Test endpoint to check if the router is working
# @router.get("/test")
# async def test_endpoint():
#     """Test endpoint to verify the router is working"""
#     return {"message": "Courses router is working", "status": "success"}


# # Endpoint for admins to create courses
# @router.post(
#     "/",
#     response_model=Dict[str, Any],
#     status_code=status.HTTP_201_CREATED,
#     summary="Create a new course",
#     description="Admin endpoint to create a new course",
# )
# async def create_course(
#     course_data: CourseCreateRequest, current_user: User = Depends(admin_required)
# ):
#     """Create a new course (Admin only)"""
#     try:
#         print(f"Creating course with data: {course_data.dict()}")
#         print(f"Current user: {current_user.email if current_user else 'None'}")

#         # Check if course code already exists
#         existing_course = await Course.find_one({"code": course_data.code})
#         if existing_course:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Course with this code already exists",
#             )

#         # Convert string sections to Section objects
#         section_objects = []
#         for i, section_name in enumerate(course_data.sections):
#             section_objects.append(
#                 Section(
#                     name=section_name,
#                     description=f"Section {i + 1}: {section_name}",
#                     order=i + 1,
#                     question_count=0,
#                 )
#             )

#         # Create new course
#         new_course = Course(
#             title=course_data.title,
#             code=course_data.code,
#             category=course_data.category,
#             sub_category=course_data.sub_category,
#             description=course_data.description,
#             sections=section_objects,
#             price=course_data.price,
#             is_free=course_data.is_free,
#             discount_percent=course_data.discount_percent,
#             material_ids=course_data.material_ids,
#             test_series_ids=course_data.test_series_ids,
#             thumbnail_url=course_data.thumbnail_url,
#             icon_url=course_data.icon_url,
#             priority_order=course_data.priority_order,
#             banner_url=course_data.banner_url,
#             tagline=course_data.tagline,
#             created_by=str(current_user.id),
#         )

#         await new_course.insert()

#         # Log admin action
#         admin_action = AdminAction(
#             admin_id=str(current_user.id),
#             action_type=ActionType.CREATE,
#             target_collection="courses",
#             target_id=str(new_course.id),
#             changes={"action": "course_created"},
#         )
#         await admin_action.insert()

#         return {
#             "message": "Course created successfully",
#             "course_id": str(new_course.id),
#         }

#     except HTTPException as e:
#         print(f"HTTPException in create_course: {e.detail}")
#         raise e
#     except Exception as e:
#         print(f"Exception in create_course: {str(e)}")
#         print(f"Exception type: {type(e)}")
#         import traceback

#         print(f"Traceback: {traceback.format_exc()}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to create course: {str(e)}",
#         )


# # Endpoint to get all courses (public)
# @router.get(
#     "/",
#     response_model=Dict[str, Any],
#     summary="List all courses",
#     description="Get a paginated list of all available courses with optional filters",
# )
# async def list_courses(
#     category: Optional[ExamCategory] = Query(
#         None, description="Filter by exam category"
#     ),
#     search: Optional[str] = Query(None, description="Search in title and description"),
#     section: Optional[str] = Query(None, description="Filter by section"),
#     is_free: Optional[bool] = Query(None, description="Filter by free courses"),
#     is_active: Optional[bool] = Query(True, description="Filter by active status"),
#     sort_by: str = Query("priority_order", description="Field to sort by"),
#     sort_order: str = Query("asc", description="Sort order (asc or desc)"),
#     page: int = Query(1, description="Page number", ge=1),
#     limit: int = Query(10, description="Items per page", ge=1, le=100),
#     current_user: Optional[User] = Depends(get_current_user),
# ):
#     """List all courses with filters and pagination"""
#     try:
#         # Build query filters
#         query_filters = {}

#         # Always filter by is_active=True for non-admin users
#         if current_user is None or current_user.role != "admin":
#             query_filters["is_active"] = True
#         elif is_active is not None:
#             query_filters["is_active"] = is_active

#         if category:
#             query_filters["category"] = category

#         if section:
#             query_filters["sections"] = {"$in": [section]}

#         if is_free is not None:
#             query_filters["is_free"] = is_free

#         if search:
#             # Search in title or description
#             query_filters["$or"] = [
#                 {"title": {"$regex": search, "$options": "i"}},
#                 {"description": {"$regex": search, "$options": "i"}},
#             ]

#         # Calculate pagination
#         skip = (page - 1) * limit

#         # Set sort order
#         sort_direction = 1 if sort_order == "asc" else -1

#         try:
#             # Fetch courses
#             courses = (
#                 await Course.find(query_filters)
#                 .sort([(sort_by, sort_direction)])
#                 .skip(skip)
#                 .limit(limit)
#                 .to_list()
#             )

#             # Count total matching courses for pagination info
#             total_courses = await Course.find(query_filters).count()
#             total_pages = (total_courses + limit - 1) // limit

#             # Convert course objects to response format
#             course_responses = []

#             for course in courses:
#                 try:
#                     # Convert Section objects to strings for response
#                     sections_list = course.get_section_names()

#                     course_data = {
#                         "id": str(course.id),
#                         "title": course.title,
#                         "code": course.code,
#                         "category": course.category.value,
#                         "sub_category": course.sub_category,
#                         "description": course.description,
#                         # "sections": sections_list,
#                         "sections": course.sections,
#                         "price": course.price,
#                         "is_free": course.is_free,
#                         "discount_percent": course.discount_percent,
#                         "thumbnail_url": course.thumbnail_url,
#                         "icon_url": getattr(course, "icon_url", None),
#                         "banner_url": getattr(course, "banner_url", None),
#                         "tagline": getattr(course, "tagline", None),
#                         "enrolled_students_count": getattr(
#                             course, "enrolled_students_count", 0
#                         ),
#                         "is_active": course.is_active,
#                         "created_at": course.created_at,
#                     }
#                     course_responses.append(course_data)
#                 except Exception as e:
#                     import traceback

#             return {
#                 "message": "Courses retrieved successfully",
#                 "data": course_responses,
#                 "pagination": {
#                     "total": total_courses,
#                     "page": page,
#                     "limit": limit,
#                     "total_pages": total_pages,
#                 },
#             }

#         except Exception as e:
#             import traceback

#             raise

#     except Exception as e:
#         import traceback

#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to retrieve courses: {str(e)}",
#         )


# # Endpoint to get enrolled courses for current user
# @router.get(
#     "/enrolled",
#     response_model=Dict[str, Any],
#     summary="Get enrolled courses",
#     description="Get all courses the current user is enrolled in",
# )
# async def get_enrolled_courses(current_user: User = Depends(get_current_user)):
#     """Get courses the current user is enrolled in"""
#     try:
#         # Initialize empty list if enrolled_courses is None
#         enrolled_course_ids = current_user.enrolled_courses or []

#         if not enrolled_course_ids:
#             return {
#                 "message": "You are not enrolled in any courses",
#                 "courses": [],
#             }

#         # Fetch all enrolled courses - Convert string IDs to ObjectIds
#         from bson import ObjectId

#         # Convert string IDs to ObjectIds for the database query
#         object_ids = []
#         for course_id in enrolled_course_ids:
#             try:
#                 object_ids.append(ObjectId(course_id))
#             except Exception as e:
#                 print(f"Invalid ObjectId: {course_id}, error: {e}")
#                 continue

#         if not object_ids:
#             return {
#                 "message": "No valid course IDs found",
#                 "courses": [],
#             }

#         courses = await Course.find(
#             {"_id": {"$in": object_ids}, "is_active": True}
#         ).to_list()

#         # Convert course objects to response format
#         course_responses = []
#         for course in courses:
#             # Convert Section objects to strings for response
#             sections_list = course.get_section_names()

#             course_responses.append(
#                 {
#                     "id": str(course.id),
#                     "title": course.title,
#                     "code": course.code,
#                     "category": course.category.value,
#                     "sub_category": course.sub_category,
#                     "description": course.description,
#                     "sections": sections_list,
#                     "thumbnail_url": course.thumbnail_url,
#                     "icon_url": course.icon_url,
#                     "material_ids": course.material_ids,
#                     "test_series_ids": course.test_series_ids,
#                 }
#             )

#         return {
#             "message": "Enrolled courses retrieved successfully",
#             "courses": course_responses,
#         }

#     except Exception as e:
#         print(f"Error in get_enrolled_courses: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to retrieve enrolled courses: {str(e)}",
#         )


# # Endpoint to get course by ID (public)
# @router.get(
#     "/{course_id}",
#     response_model=Dict[str, Any],
#     summary="Get course details",
#     description="Get detailed information about a specific course",
# )
# async def get_course(course_id: str):
#     """Get course details by ID"""
#     try:
#         course = await Course.get(course_id)
#         if not course:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="Course not found",
#             )

#         # For inactive courses, only admins should be able to view them
#         # This is handled in the frontend by checking user role

#         # Convert Section objects to strings for response
#         sections_list = course.get_section_names()

#         return {
#             "message": "Course retrieved successfully",
#             "course": {
#                 "id": str(course.id),
#                 "title": course.title,
#                 "code": course.code,
#                 "category": course.category.value,
#                 "sub_category": course.sub_category,
#                 "description": course.description,
#                 "sections": sections_list,
#                 "price": course.price,
#                 "is_free": course.is_free,
#                 "discount_percent": course.discount_percent,
#                 "material_ids": course.material_ids,
#                 "test_series_ids": course.test_series_ids,
#                 "thumbnail_url": course.thumbnail_url,
#                 "icon_url": course.icon_url,
#                 "banner_url": course.banner_url,
#                 "tagline": course.tagline,
#                 "enrolled_students_count": course.enrolled_students_count,
#                 "is_active": course.is_active,
#                 "created_at": course.created_at,
#                 "updated_at": course.updated_at,
#             },
#         }

#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to retrieve course: {str(e)}",
#         )


# # Endpoint to update course (admin only)
# @router.put(
#     "/{course_id}",
#     response_model=Dict[str, Any],
#     summary="Update course",
#     description="Admin endpoint to update course details",
# )
# async def update_course(
#     course_id: str,
#     course_data: CourseUpdateRequest,
#     current_user: User = Depends(admin_required),
# ):
#     """Update course details (Admin only)"""
#     try:
#         course = await Course.get(course_id)
#         if not course:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="Course not found",
#             )

#         # Track changes for audit log
#         changes = {}

#         # Update fields if provided
#         for field, value in course_data.dict(exclude_unset=True).items():
#             if value is not None:
#                 setattr(course, field, value)
#                 changes[field] = (
#                     str(value) if not isinstance(value, list) else "updated"
#                 )

#         # Only update if there are changes
#         if changes:
#             course.update_timestamp()
#             await course.save()

#             # Log admin action
#             admin_action = AdminAction(
#                 admin_id=str(current_user.id),
#                 action_type=ActionType.UPDATE,
#                 target_collection="courses",
#                 target_id=course_id,
#                 changes=changes,
#             )
#             await admin_action.insert()

#             return {
#                 "message": "Course updated successfully",
#                 "course_id": course_id,
#                 "changes": changes,
#             }
#         else:
#             return {
#                 "message": "No changes to apply",
#                 "course_id": course_id,
#             }

#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to update course: {str(e)}",
#         )


# # Endpoint to delete course (admin only - soft delete)
# @router.delete(
#     "/{course_id}",
#     response_model=Dict[str, Any],
#     summary="Delete course",
#     description="Admin endpoint to delete (deactivate) a course",
# )
# async def delete_course(course_id: str, current_user: User = Depends(admin_required)):
#     """Delete (deactivate) a course (Admin only)"""
#     try:
#         course = await Course.get(course_id)
#         if not course:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="Course not found",
#             )

#         # Check if course is already inactive
#         if not course.is_active:
#             return {
#                 "message": "Course is already deactivated",
#                 "course_id": course_id,
#             }

#         # Soft delete by setting is_active=False
#         course.is_active = False
#         course.update_timestamp()
#         await course.save()

#         # Log admin action
#         admin_action = AdminAction(
#             admin_id=str(current_user.id),
#             action_type=ActionType.DELETE,
#             target_collection="courses",
#             target_id=course_id,
#             changes={"is_active": False},
#         )
#         await admin_action.insert()

#         return {
#             "message": "Course deactivated successfully",
#             "course_id": course_id,
#         }

#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to delete course: {str(e)}",
#         )


# # Endpoint to enroll in a course (for students)
# @router.post(
#     "/{course_id}/enroll",
#     response_model=Dict[str, Any],
#     summary="Enroll in course",
#     description="Student endpoint to enroll in a course",
# )
# async def enroll_in_course(
#     course_id: str,
#     current_user: User = Depends(get_current_user),
# ):
#     """Enroll in a course (Student only)"""
#     try:
#         course = await Course.get(course_id)
#         if not course:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="Course not found",
#             )

#         if not course.is_active:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="This course is currently not available",
#             )

#         # Check if already enrolled
#         if course_id in current_user.enrolled_courses:
#             return {
#                 "message": "You are already enrolled in this course",
#                 "course_id": course_id,
#                 "course_title": course.title,
#             }

#         # For free courses, enroll directly
#         if course.is_free:
#             # Add course to user's enrolled courses
#             if course_id not in current_user.enrolled_courses:
#                 current_user.enrolled_courses.append(course_id)
#                 current_user.update_timestamp()
#                 await current_user.save()

#                 # Increment enrolled students count
#                 course.enrolled_students_count += 1
#                 course.update_timestamp()
#                 await course.save()

#                 return {
#                     "message": "Successfully enrolled in free course",
#                     "course_id": course_id,
#                     "course_title": course.title,
#                 }
#         else:
#             # For paid courses, check if the user has premium access or has purchased this course
#             if current_user.has_premium_access:
#                 # Premium users can access all courses
#                 if course_id not in current_user.enrolled_courses:
#                     current_user.enrolled_courses.append(course_id)
#                     current_user.update_timestamp()
#                     await current_user.save()

#                     # Increment enrolled students count
#                     course.enrolled_students_count += 1
#                     course.update_timestamp()
#                     await course.save()

#                     return {
#                         "message": "Successfully enrolled with premium access",
#                         "course_id": course_id,
#                         "course_title": course.title,
#                     }
#             else:
#                 # Redirect to payment flow for non-premium users
#                 # The actual enrollment will happen after payment confirmation
#                 price = course.price
#                 if course.discount_percent:
#                     discount_amount = (course.price * course.discount_percent) / 100
#                     price = course.price - discount_amount

#                 return {
#                     "message": "Payment required to enroll in this course",
#                     "course_id": course_id,
#                     "course_title": course.title,
#                     "price": price,
#                     "original_price": course.price,
#                     "discount_percent": course.discount_percent,
#                     "requires_payment": True,
#                 }

#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to enroll in course: {str(e)}",
#         )


# # Endpoint to add material to a course (admin only)
# @router.post(
#     "/{course_id}/materials",
#     response_model=Dict[str, Any],
#     summary="Add material to course",
#     description="Admin endpoint to add study material to a course",
# )
# async def add_material_to_course(
#     course_id: str,
#     data: Dict[str, Any],
#     current_user: User = Depends(admin_required),
# ):
#     """Add study material to a course (Admin only)"""
#     try:
#         course = await Course.get(course_id)
#         if not course:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="Course not found",
#             )

#         material_id = data.get("material_id")
#         if not material_id:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Material ID is required",
#             )

#         # Check if material ID already exists in the course
#         if material_id in course.material_ids:
#             return {
#                 "message": "Material already added to this course",
#                 "course_id": course_id,
#                 "material_id": material_id,
#             }

#         # Add material to course
#         course.material_ids.append(material_id)
#         course.update_timestamp()
#         await course.save()

#         # Log admin action
#         admin_action = AdminAction(
#             admin_id=str(current_user.id),
#             action_type=ActionType.UPDATE,
#             target_collection="courses",
#             target_id=course_id,
#             changes={"action": "material_added", "material_id": material_id},
#         )
#         await admin_action.insert()

#         return {
#             "message": "Material added to course successfully",
#             "course_id": course_id,
#             "material_id": material_id,
#         }

#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to add material to course: {str(e)}",
#         )


# # Endpoint to add test series to a course (admin only)
# @router.post(
#     "/{course_id}/test-series",
#     response_model=Dict[str, Any],
#     summary="Add test series to course",
#     description="Admin endpoint to add test series to a course",
# )
# async def add_test_series_to_course(
#     course_id: str,
#     data: Dict[str, Any],
#     current_user: User = Depends(admin_required),
# ):
#     """Add test series to a course (Admin only)"""
#     try:
#         course = await Course.get(course_id)
#         if not course:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="Course not found",
#             )

#         test_series_id = data.get("test_series_id")
#         if not test_series_id:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Test series ID is required",
#             )

#         # Check if test series ID already exists in the course
#         if test_series_id in course.test_series_ids:
#             return {
#                 "message": "Test series already added to this course",
#                 "course_id": course_id,
#                 "test_series_id": test_series_id,
#             }

#         # Add test series to course
#         course.test_series_ids.append(test_series_id)
#         course.update_timestamp()
#         await course.save()

#         # Log admin action
#         admin_action = AdminAction(
#             admin_id=str(current_user.id),
#             action_type=ActionType.UPDATE,
#             target_collection="courses",
#             target_id=course_id,
#             changes={"action": "test_series_added", "test_series_id": test_series_id},
#         )
#         await admin_action.insert()

#         return {
#             "message": "Test series added to course successfully",
#             "course_id": course_id,
#             "test_series_id": test_series_id,
#         }

#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to add test series to course: {str(e)}",
#         )


# # Endpoint to remove material from a course (admin only)
# @router.delete(
#     "/{course_id}/materials/{material_id}",
#     response_model=Dict[str, Any],
#     summary="Remove material from course",
#     description="Admin endpoint to remove study material from a course",
# )
# async def remove_material_from_course(
#     course_id: str,
#     material_id: str,
#     current_user: User = Depends(admin_required),
# ):
#     """Remove study material from a course (Admin only)"""
#     try:
#         course = await Course.get(course_id)
#         if not course:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="Course not found",
#             )

#         # Check if material exists in course
#         if material_id not in course.material_ids:
#             return {
#                 "message": "Material not found in this course",
#                 "course_id": course_id,
#                 "material_id": material_id,
#             }

#         # Remove material from course
#         course.material_ids.remove(material_id)
#         course.update_timestamp()
#         await course.save()

#         # Log admin action
#         admin_action = AdminAction(
#             admin_id=str(current_user.id),
#             action_type=ActionType.UPDATE,
#             target_collection="courses",
#             target_id=course_id,
#             changes={"action": "material_removed", "material_id": material_id},
#         )
#         await admin_action.insert()

#         return {
#             "message": "Material removed from course successfully",
#             "course_id": course_id,
#             "material_id": material_id,
#         }

#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to remove material from course: {str(e)}",
#         )


# # Endpoint to remove test series from a course (admin only)
# @router.delete(
#     "/{course_id}/test-series/{test_series_id}",
#     response_model=Dict[str, Any],
#     summary="Remove test series from course",
#     description="Admin endpoint to remove a test series from a course",
# )
# async def remove_test_series_from_course(
#     course_id: str,
#     test_series_id: str,
#     current_user: User = Depends(admin_required),
# ):
#     """Remove test series from a course (Admin only)"""
#     try:
#         # Validate course_id format
#         if not ObjectId.is_valid(course_id):
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Invalid course ID format",
#             )

#         # Find the course
#         course = await Course.get(course_id)
#         if not course:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
#             )

#         # Remove test series ID if it exists
#         if test_series_id in course.test_series_ids:
#             course.test_series_ids.remove(test_series_id)
#             await course.save()

#         # Log admin action
#         admin_action = AdminAction(
#             admin_id=str(current_user.id),
#             action_type=ActionType.UPDATE,
#             target_collection="courses",
#             target_id=course_id,
#             changes={"action": "test_series_removed", "test_series_id": test_series_id},
#         )
#         await admin_action.insert()

#         return {"status": "success", "message": "Test series removed from course"}
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to remove test series from course: {str(e)}",
#         )


# @router.post(
#     "/upload-questions",
#     response_model=Dict[str, Any],
#     status_code=status.HTTP_201_CREATED,
#     summary="Upload questions to a course section",
#     description="Upload questions to a specific section in a course via CSV",
# )
# async def upload_questions_to_section(
#     file: UploadFile = File(...),
#     course_id: str = Form(...),
#     section: str = Form(...),
#     current_user: User = Depends(admin_required),
# ):
#     """Upload questions to a specific section in a course"""
#     try:
#         # Validate course_id
#         if not ObjectId.is_valid(course_id):
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Invalid course ID format",
#             )

#         # Get the course
#         course = await Course.get(course_id)
#         if not course:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
#             )

#         # Validate section exists in course
#         section_names = course.get_section_names()
#         if not section_names or section not in section_names:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail=f"Section '{section}' not found in course",
#             )

#         # Read and parse CSV file
#         contents = await file.read()
#         text = contents.decode("utf-8")
#         csv_reader = csv.DictReader(io.StringIO(text))

#         questions = []
#         for row in csv_reader:
#             try:
#                 # Extract options with correct format
#                 options = []
#                 correct_answer = row.get("correct_answer", "").strip().upper()
#                 remarks = row.get("remarks", "").strip()
#                 for i, opt_key in enumerate(
#                     ["option_a", "option_b", "option_c", "option_d"]
#                 ):
#                     opt_text = row.get(opt_key, "").strip()
#                     if opt_text:
#                         option_letter = chr(65 + i)  # A, B, C, D
#                         options.append(
#                             QuestionOption(
#                                 text=opt_text,
#                                 is_correct=option_letter == correct_answer,
#                                 order=i,
#                             )
#                         )

#                 # Get question text and create title
#                 question_text = row.get("question", "").strip()
#                 title = question_text[:50] + ("..." if len(question_text) > 50 else "")

#                 # Extract explanation and remarks
#                 explanation = row.get("explanation", "").strip() or None

#                 # Map CSV row to Question model
#                 question = Question(
#                     title=title,
#                     question_text=question_text,
#                     question_type=QuestionType.MCQ,
#                     difficulty_level=DifficultyLevel.MEDIUM,  # Default difficulty
#                     course_id=course_id,
#                     section=section,
#                     options=options,
#                     explanation=explanation,
#                     remarks=remarks or None,
#                     subject=row.get("subject", "General").strip(),
#                     topic=row.get("topic", "General").strip(),
#                     tags=[],
#                     created_by=str(current_user.id),
#                 )
#                 questions.append(question)
#             except Exception as e:
#                 print(f"Error processing row: {row}. Error: {str(e)}")
#                 continue

#         # Save questions to database
#         if questions:
#             await Question.insert_many(questions)
#         print("hello gurrakkha", questions)

#         # Log admin action
#         admin_action = AdminAction(
#             admin_id=str(current_user.id),
#             action_type=ActionType.CREATE,
#             target_collection="questions",
#             target_id=course_id,
#             changes={
#                 "action": "questions_uploaded",
#                 "count": len(questions),
#                 "section": section,
#             },
#         )
#         await admin_action.insert()

#         return {
#             "status": "success",
#             "message": f"Successfully uploaded {len(questions)} questions to section '{section}'",
#             "count": len(questions),
#         }

#     except HTTPException:
#         raise
#     except Exception as e:
#         print(f"Error in upload_questions_to_section: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to upload questions: {str(e)}",
#         )


# # added by manpreet
# @router.get(
#     "/{course_id}/sections/{section_name}/questions",
#     response_model=Dict[str, Any],
#     summary="Get questions for course section",
#     description="Get all questions for a specific section in a course or random mock questions",
# )
# async def get_section_questions(
#     course_id: str,
#     section_name: str,
#     page: int = Query(1, description="Page number", ge=1),
#     limit: int = Query(10, description="Items per page", ge=1, le=100),
#     difficulty: Optional[str] = Query(None, description="Filter by difficulty"),
#     topic: Optional[str] = Query(None, description="Filter by topic"),
#     mode: Optional[str] = Query(None, description="Mode: normal | mock"),
#     current_user: Optional[User] = Depends(get_current_user),
# ):
#     """
#     Get questions for a specific section in a course.
#     - `mode=normal` (default): Paginated, filtered results.
#     - `mode=mock`: Fetch random N questions based on section.question_count.
#     """
#     try:
#         if not ObjectId.is_valid(course_id):
#             raise HTTPException(status_code=400, detail="Invalid course ID format")

#         course = await Course.get(course_id)
#         if not course:
#             raise HTTPException(status_code=404, detail="Course not found")

#         section = course.get_section(section_name)
#         if not section:
#             raise HTTPException(
#                 status_code=404,
#                 detail=f"Section '{section_name}' not found in course",
#             )

#         # --------------------------------
#         # MOCK MODE
#         # --------------------------------
#         if (mode or "").lower() == "mock":
#             question_limit = int(section.question_count or 0)
#             if question_limit <= 0:
#                 return {
#                     "message": f"No questions configured for section '{section_name}'",
#                     "course": {
#                         "id": str(course.id),
#                         "title": course.title,
#                         "code": course.code,
#                     },
#                     "section": section_name,
#                     "questions": [],
#                     "pagination": {
#                         "total": 0,
#                         "limit": question_limit,
#                         "page": 1,
#                         "total_pages": 0,
#                     },
#                 }

#             from motor.motor_asyncio import AsyncIOMotorClient

#             _client = AsyncIOMotorClient(settings.MONGO_URI)
#             db = _client.get_default_database()
#             collection = db["questions"]

#             pipeline = [
#                 {"$match": {"course_id": course_id, "section": section_name}},
#                 {"$sample": {"size": question_limit}},
#             ]

#             cursor = collection.aggregate(pipeline)

#             questions = []
#             async for doc in cursor:
#                 if "_id" in doc:
#                     doc["id"] = str(doc["_id"])
#                 questions.append(doc)

#             total_questions = len(questions)
#             total_pages = 1

#         # --------------------------------
#         # NORMAL MODE
#         # --------------------------------
#         else:
#             query_filters = {"course_id": course_id, "section": section_name}
#             if difficulty:
#                 query_filters["difficulty_level"] = difficulty.upper()
#             if topic:
#                 query_filters["topic"] = {"$regex": topic, "$options": "i"}

#             skip = (page - 1) * limit
#             questions = (
#                 await Question.find(query_filters)
#                 .sort([("created_at", -1)])
#                 .skip(skip)
#                 .limit(limit)
#                 .to_list()
#             )

#             total_questions = await Question.find(query_filters).count()
#             total_pages = (total_questions + limit - 1) // limit

#         # --------------------------------
#         # FORMAT RESPONSE (handle dicts + Beanie models)
#         # --------------------------------
#         question_data = []
#         for q in questions:
#             if isinstance(q, dict):  # MOCK MODE
#                 options_with_images = [
#                     {
#                         "text": opt.get("text"),
#                         "is_correct": opt.get("is_correct", False),
#                         "order": opt.get("order"),
#                     }
#                     for opt in q.get("options", [])
#                 ]

#                 question_data.append(
#                     {
#                         "id": str(q.get("id", q.get("_id"))),
#                         "title": q.get("title"),
#                         "question_text": q.get("question_text"),
#                         "question_type": q.get("question_type"),
#                         "difficulty_level": q.get("difficulty_level"),
#                         "options": options_with_images,
#                         "explanation": q.get("explanation"),
#                         "remarks": q.get("remarks"),
#                         "subject": q.get("subject"),
#                         "topic": q.get("topic"),
#                         "tags": q.get("tags", []),
#                         "marks": q.get("marks", 1.0),
#                         "created_at": q.get("created_at"),
#                         "updated_at": q.get("updated_at"),
#                         "is_active": q.get("is_active", True),
#                         "created_by": q.get("created_by"),
#                     }
#                 )
#             else:  # NORMAL MODE
#                 options_with_images = [
#                     {
#                         "text": option.text,
#                         "is_correct": option.is_correct,
#                         "order": option.order,
#                     }
#                     for option in q.options
#                 ]

#                 question_data.append(
#                     {
#                         "id": str(q.id),
#                         "title": q.title,
#                         "question_text": q.question_text,
#                         "question_type": getattr(
#                             q.question_type, "value", str(q.question_type)
#                         ),
#                         "difficulty_level": getattr(
#                             q.difficulty_level, "value", str(q.difficulty_level)
#                         ),
#                         "options": options_with_images,
#                         "explanation": q.explanation,
#                         "remarks": q.remarks,
#                         "subject": q.subject,
#                         "topic": q.topic,
#                         "tags": q.tags,
#                         "marks": getattr(q, "marks", 1.0),
#                         "created_at": q.created_at,
#                         "updated_at": q.updated_at,
#                         "is_active": q.is_active,
#                         "created_by": q.created_by,
#                     }
#                 )

#         return {
#             "message": (
#                 f"Random {section.question_count} questions for section '{section_name}' (mock mode)"
#                 if (mode or "").lower() == "mock"
#                 else f"Questions for section '{section_name}' retrieved successfully"
#             ),
#             "course": {
#                 "id": str(course.id),
#                 "title": course.title,
#                 "code": course.code,
#             },
#             "section": section_name,
#             "questions": question_data,
#             "pagination": (
#                 {
#                     "total": total_questions,
#                     "limit": section.question_count,
#                     "page": 1,
#                     "total_pages": total_pages,
#                 }
#                 if (mode or "").lower() == "mock"
#                 else {
#                     "total": total_questions,
#                     "page": page,
#                     "limit": limit,
#                     "total_pages": total_pages,
#                 }
#             ),
#         }

#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         raise HTTPException(
#             status_code=500, detail=f"Failed to retrieve section questions: {str(e)}"
#         )


# # Endpoint to get section details
# @router.get(
#     "/{course_id}/sections/{section_name}",
#     response_model=Dict[str, Any],
#     summary="Get section details",
#     description="Get details about a specific section in a course",
# )
# async def get_section_details(
#     course_id: str,
#     section_name: str,
#     current_user: Optional[User] = Depends(get_current_user),
# ):
#     """Get details for a specific section in a course"""
#     try:
#         # Validate course_id
#         if not ObjectId.is_valid(course_id):
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Invalid course ID format",
#             )

#         # Get the course
#         course = await Course.get(course_id)
#         if not course:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
#             )

#         # Find the section
#         section = course.get_section(section_name)
#         if not section:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail=f"Section '{section_name}' not found in course",
#             )

#         # Get question count for this section
#         question_count = await Question.find(
#             {
#                 "course_id": course_id,
#                 "section": section_name,
#             }
#         ).count()

#         return {
#             "message": f"Section '{section_name}' details retrieved successfully",
#             "course": {
#                 "id": str(course.id),
#                 "title": course.title,
#                 "code": course.code,
#             },
#             "section": {
#                 "name": section.name,
#                 "description": section.description,
#                 "question_count": question_count,
#                 "order": section.order,
#             },
#         }

#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to retrieve section details: {str(e)}",
#         )


# # Endpoint to list all sections for a course
# @router.get(
#     "/{course_id}/sections",
#     response_model=Dict[str, Any],
#     summary="List course sections",
#     description="Get all sections for a specific course",
# )
# async def list_course_sections(
#     course_id: str,
#     current_user: Optional[User] = Depends(get_current_user),
# ):
#     """List all sections for a course"""
#     try:
#         # Validate course_id
#         if not ObjectId.is_valid(course_id):
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Invalid course ID format",
#             )

#         # Get the course
#         course = await Course.get(course_id)
#         if not course:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
#             )

#         # Get question counts for each section
#         sections_with_counts = []
#         for section in course.sections:
#             question_count = await Question.find(
#                 {
#                     "course_id": course_id,
#                     "section": section.name,
#                 }
#             ).count()

#             sections_with_counts.append(
#                 {
#                     "name": section.name,
#                     "description": section.description,
#                     "question_count": question_count,
#                     "order": section.order,
#                 }
#             )

#         return {
#             "message": f"Sections for course '{course.title}' retrieved successfully",
#             "course": {
#                 "id": str(course.id),
#                 "title": course.title,
#                 "code": course.code,
#             },
#             "sections": sections_with_counts,
#         }

#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to retrieve course sections: {str(e)}",
#         )


# # Section Management Endpoints


# class SectionCreateRequest(BaseModel):
#     section_name: str


# class SectionUpdateRequest(BaseModel):
#     new_section_name: str


# @router.post(
#     "/{course_id}/sections",
#     response_model=Dict[str, Any],
#     status_code=status.HTTP_201_CREATED,
#     summary="Add section to course",
#     description="Admin endpoint to add a new section to a course",
# )
# async def add_section_to_course(
#     course_id: str,
#     section_data: SectionCreateRequest,
#     current_user: User = Depends(admin_required),
# ):
#     """Add a new section to a course (Admin only)"""
#     try:
#         # Validate course_id
#         if not ObjectId.is_valid(course_id):
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Invalid course ID format",
#             )

#         # Get the course
#         course = await Course.get(course_id)
#         if not course:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
#             )

#         # Check if section already exists
#         if course.get_section(section_data.section_name):
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Section with this name already exists",
#             )

#         # Create new section
#         new_section = Section(
#             name=section_data.section_name,
#             description=f"Section: {section_data.section_name}",
#             order=len(course.sections) + 1,
#             question_count=0,
#         )

#         # Add section to course
#         course.sections.append(new_section)
#         course.update_timestamp()
#         await course.save()

#         # Log admin action
#         admin_action = AdminAction(
#             admin_id=str(current_user.id),
#             action_type=ActionType.CREATE,
#             target_collection="courses",
#             target_id=course_id,
#             changes={
#                 "action": "section_added",
#                 "section_name": section_data.section_name,
#             },
#         )
#         await admin_action.insert()

#         return {
#             "message": f"Section '{section_data.section_name}' added successfully",
#             "course_id": course_id,
#             "section": {
#                 "name": new_section.name,
#                 "description": new_section.description,
#                 "order": new_section.order,
#                 "question_count": new_section.question_count,
#             },
#         }

#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to add section: {str(e)}",
#         )


# @router.put(
#     "/{course_id}/sections/{section_name}",
#     response_model=Dict[str, Any],
#     summary="Update section name",
#     description="Admin endpoint to rename a section in a course",
# )
# async def update_section_in_course(
#     course_id: str,
#     section_name: str,
#     section_data: SectionUpdateRequest,
#     current_user: User = Depends(admin_required),
# ):
#     """Update a section name in a course (Admin only)"""
#     try:
#         # Validate course_id
#         if not ObjectId.is_valid(course_id):
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Invalid course ID format",
#             )

#         # Get the course
#         course = await Course.get(course_id)
#         if not course:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
#             )

#         # Find the section
#         section = course.get_section(section_name)
#         if not section:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail=f"Section '{section_name}' not found",
#             )

#         # Check if new name already exists
#         if course.get_section(section_data.new_section_name):
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Section with this name already exists",
#             )

#         # Update section name
#         old_name = section.name
#         section.name = section_data.new_section_name
#         section.description = f"Section: {section_data.new_section_name}"

#         # Update questions in this section to use new section name
#         await Question.find({"course_id": course_id, "section": old_name}).update_many(
#             {"$set": {"section": section_data.new_section_name}}
#         )

#         course.update_timestamp()
#         await course.save()

#         # Log admin action
#         admin_action = AdminAction(
#             admin_id=str(current_user.id),
#             action_type=ActionType.UPDATE,
#             target_collection="courses",
#             target_id=course_id,
#             changes={
#                 "action": "section_renamed",
#                 "old_name": old_name,
#                 "new_name": section_data.new_section_name,
#             },
#         )
#         await admin_action.insert()

#         return {
#             "message": f"Section renamed from '{old_name}' to '{section_data.new_section_name}' successfully",
#             "course_id": course_id,
#             "old_name": old_name,
#             "new_name": section_data.new_section_name,
#         }

#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to update section: {str(e)}",
#         )


# @router.delete(
#     "/{course_id}/sections/{section_name}",
#     response_model=Dict[str, Any],
#     summary="Delete section from course",
#     description="Admin endpoint to delete a section and all its questions from a course",
# )
# async def delete_section_from_course(
#     course_id: str,
#     section_name: str,
#     current_user: User = Depends(admin_required),
# ):
#     """Delete a section and all its questions from a course (Admin only)"""
#     try:
#         # Validate course_id
#         if not ObjectId.is_valid(course_id):
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Invalid course ID format",
#             )

#         # Get the course
#         course = await Course.get(course_id)
#         if not course:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
#             )

#         # Find the section
#         section = course.get_section(section_name)
#         if not section:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail=f"Section '{section_name}' not found",
#             )

#         # Delete all questions in this section
#         deleted_questions = await Question.find(
#             {"course_id": course_id, "section": section_name}
#         ).delete_many()

#         # Remove section from course
#         course.sections = [s for s in course.sections if s.name != section_name]

#         # Update order of remaining sections
#         for i, remaining_section in enumerate(course.sections):
#             remaining_section.order = i + 1

#         course.update_timestamp()
#         await course.save()

#         # Log admin action
#         admin_action = AdminAction(
#             admin_id=str(current_user.id),
#             action_type=ActionType.DELETE,
#             target_collection="courses",
#             target_id=course_id,
#             changes={
#                 "action": "section_deleted",
#                 "section_name": section_name,
#                 "deleted_questions_count": deleted_questions,
#             },
#         )
#         await admin_action.insert()

#         return {
#             "message": f"Section '{section_name}' and {deleted_questions} questions deleted successfully",
#             "course_id": course_id,
#             "deleted_questions_count": deleted_questions,
#         }

#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to delete section: {str(e)}",
#         )


# # manpreet ne add kiya hai.


# def str_to_bool(value: str) -> Optional[bool]:
#     if value is None:
#         return None
#     if value.lower() in ["true", "1", "yes"]:
#         return True
#     if value.lower() in ["false", "0", "no"]:
#         return False
#     return None


# @router.get("/tests")
# async def list_tests(is_free: Optional[str] = None):
#     query = {}
#     parsed_bool = str_to_bool(is_free)
#     if parsed_bool is not None:
#         query["is_free"] = parsed_bool

#     tests = await Test.find(query).to_list()
#     return {"items": tests, "message": "Tests retrieved successfully"}


# @router.put("/{course_id}/sections/{section_name}/question-count")
# async def update_section_question_count(
#     course_id: str, section_name: str, new_count: int = Body(..., embed=True)
# ):
#     course = await Course.get(course_id)
#     if not course:
#         raise HTTPException(status_code=404, detail="Course not found")

#     section = course.get_section(section_name)
#     if not section:
#         raise HTTPException(status_code=404, detail="Section not found")

#     section.question_count = new_count
#     await course.save()
#     return {"message": "Question count updated", "section": section}


# # -------------------------------
# # Mock submission (course-based)
# # -------------------------------


# class MockSubmitAnswer(BaseModel):
#     question_id: str
#     selected_option_order: Optional[int] = None
#     selected_option_text: Optional[str] = None


# class MockSubmitRequest(BaseModel):
#     answers: List[MockSubmitAnswer]
#     time_spent_seconds: Optional[int] = 0
#     marked_for_review: Optional[List[str]] = []


# @router.post(
#     "/{course_id}/mock/submit",
#     response_model=Dict[str, Any],
#     summary="Submit course-based mock answers",
#     description=(
#         "Submit answers for a course/section-based mock test and receive scored results.\n"
#         "Accepts either selected_option_order or selected_option_text for each answer."
#     ),
# )
# async def submit_course_mock(
#     course_id: str,
#     payload: MockSubmitRequest,
#     current_user: User = Depends(get_current_user),
# ):
#     """Score submitted answers for a course-based mock without persisting attempts."""
#     try:
#         # Validate course
#         if not ObjectId.is_valid(course_id):
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Invalid course ID format",
#             )

#         course = await Course.get(course_id)
#         if not course:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
#             )

#         # Collect question IDs
#         question_ids: List[str] = [
#             a.question_id for a in payload.answers if a.question_id
#         ]
#         if not question_ids:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST, detail="No answers provided"
#             )

#         # Convert string IDs to ObjectId for MongoDB query
#         try:
#             object_ids = [ObjectId(qid) for qid in question_ids]
#         except Exception:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Invalid question ID format",
#             )

#         # Fetch questions in bulk
#         questions = await Question.find({"_id": {"$in": object_ids}}).to_list()

#         # Debug logging
#         print(
#             f"DEBUG: Found {len(questions)} questions out of {len(question_ids)} requested"
#         )
#         print(f"DEBUG: Question IDs requested: {question_ids}")
#         print(f"DEBUG: Question IDs found: {[str(q.id) for q in questions]}")

#         # Index answers and questions
#         answer_by_qid: Dict[str, MockSubmitAnswer] = {
#             a.question_id: a for a in payload.answers
#         }
#         question_by_id: Dict[str, Question] = {}
#         for q in questions:
#             # Beanie id may be ObjectId; cast to str
#             question_by_id[str(q.id)] = q

#         # Scoring
#         total_questions = len(questions)
#         attempted = 0
#         correct = 0
#         per_section: Dict[str, Dict[str, int]] = {}
#         question_results: List[Dict[str, Any]] = []

#         for qid, q in question_by_id.items():
#             ans = answer_by_qid.get(qid)
#             if not ans:
#                 # unanswered
#                 section_name = getattr(q, "section", "General") or "General"
#                 per_section.setdefault(
#                     section_name, {"total": 0, "attempted": 0, "correct": 0}
#                 )
#                 per_section[section_name]["total"] += 1
#                 question_results.append(
#                     {
#                         "question_id": qid,
#                         "section": section_name,
#                         "attempted": False,
#                         "is_correct": False,
#                         "selected_option_order": None,
#                         "correct_option_order": next(
#                             (o.order for o in q.options if o.is_correct), None
#                         ),
#                     }
#                 )
#                 continue

#             section_name = getattr(q, "section", "General") or "General"
#             per_section.setdefault(
#                 section_name, {"total": 0, "attempted": 0, "correct": 0}
#             )
#             per_section[section_name]["total"] += 1

#             # Determine selected order
#             selected_order = ans.selected_option_order
#             if selected_order is None and ans.selected_option_text is not None:
#                 # Try to map by text (trim/normalize spaces)
#                 normalized = ans.selected_option_text.strip()
#                 for opt in q.options:
#                     if (opt.text or "").strip() == normalized:
#                         selected_order = opt.order
#                         break

#             if selected_order is None:
#                 # treated as unanswered
#                 question_results.append(
#                     {
#                         "question_id": qid,
#                         "section": section_name,
#                         "attempted": False,
#                         "is_correct": False,
#                         "selected_option_order": None,
#                         "correct_option_order": next(
#                             (o.order for o in q.options if o.is_correct), None
#                         ),
#                     }
#                 )
#                 continue

#             attempted += 1
#             per_section[section_name]["attempted"] += 1

#             correct_order = next((o.order for o in q.options if o.is_correct), None)
#             is_correct = correct_order is not None and selected_order == correct_order
#             if is_correct:
#                 correct += 1
#                 per_section[section_name]["correct"] += 1

#             question_results.append(
#                 {
#                     "question_id": qid,
#                     "section": section_name,
#                     "attempted": True,
#                     "is_correct": is_correct,
#                     "selected_option_order": selected_order,
#                     "correct_option_order": correct_order,
#                 }
#             )

#         max_score = total_questions  # 1 mark per question for mock
#         score = correct
#         accuracy = (correct / attempted) if attempted > 0 else 0.0

#         section_summaries = [
#             {
#                 "section": name,
#                 "total": data["total"],
#                 "attempted": data["attempted"],
#                 "correct": data["correct"],
#                 "accuracy": (
#                     (data["correct"] / data["attempted"])
#                     if data["attempted"] > 0
#                     else 0.0
#                 ),
#             }
#             for name, data in per_section.items()
#         ]

#         return {
#             "message": "Mock submission scored successfully",
#             "results": {
#                 "course": {
#                     "id": str(course.id),
#                     "title": course.title,
#                     "code": course.code,
#                 },
#                 "user_id": str(current_user.id),
#                 "time_spent_seconds": payload.time_spent_seconds or 0,
#                 "total_questions": total_questions,
#                 "attempted_questions": attempted,
#                 "correct_answers": correct,
#                 "score": score,
#                 "max_score": max_score,
#                 "percentage": (
#                     round((score / max_score) * 100, 2) if max_score > 0 else 0
#                 ),
#                 "accuracy": round(accuracy, 4),
#                 "section_summaries": section_summaries,
#                 "question_results": question_results,
#                 "marked_for_review": payload.marked_for_review or [],
#             },
#         }

#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to submit mock answers: {str(e)}",
#         )
