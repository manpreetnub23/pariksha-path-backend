# from fastapi import APIRouter, HTTPException, Depends, status
# from typing import Dict, Any, Optional
# from ..models.exam_category_structure import ExamCategoryStructure
# from ..models.admin_action import AdminAction, ActionType
# from ..models.user import User
# from ..dependencies import admin_required, get_current_user

# router = APIRouter(prefix="/api/v1/exam-categories", tags=["Exam Categories"])


# @router.get(
#     "/",
#     response_model=Dict[str, Any],
#     summary="Get exam category structure",
#     description="Get the hierarchical structure of exam categories and subcategories",
# )
# async def get_exam_structure():
#     """Get the structure of all exam categories and subcategories"""
#     try:
#         # Get the active structure
#         structure = await ExamCategoryStructure.find_one({"is_active": True})

#         if not structure:
#             return {"message": "No exam category structure found", "structure": {}}

#         return {
#             "message": "Exam category structure retrieved successfully",
#             "version": structure.version,
#             "structure": structure.structure,
#         }

#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to retrieve exam structure: {str(e)}",
#         )


# @router.post(
#     "/",
#     response_model=Dict[str, Any],
#     status_code=status.HTTP_201_CREATED,
#     summary="Create or update exam structure",
#     description="Admin endpoint to create or update the exam category structure",
# )
# async def create_exam_structure(
#     data: Dict[str, Any],
#     current_user: User = Depends(admin_required),
# ):
#     """Create or update the exam category structure (Admin only)"""
#     try:
#         structure_data = data.get("structure")
#         if not structure_data:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Structure data is required",
#             )

#         # Find existing active structure
#         existing_structure = await ExamCategoryStructure.find_one({"is_active": True})

#         if existing_structure:
#             # Update existing structure
#             existing_structure.structure = structure_data
#             existing_structure.version += 1
#             existing_structure.update_timestamp()
#             await existing_structure.save()

#             # Log admin action
#             admin_action = AdminAction(
#                 admin_id=str(current_user.id),
#                 action_type=ActionType.UPDATE,
#                 target_collection="exam_category_structure",
#                 target_id=str(existing_structure.id),
#                 changes={
#                     "action": "exam_structure_updated",
#                     "version": existing_structure.version,
#                 },
#             )
#             await admin_action.insert()

#             return {
#                 "message": "Exam category structure updated successfully",
#                 "version": existing_structure.version,
#                 "id": str(existing_structure.id),
#             }
#         else:
#             # Create new structure
#             new_structure = ExamCategoryStructure(
#                 structure=structure_data,
#                 version=1,
#                 created_by=str(current_user.id),
#             )
#             await new_structure.insert()

#             # Log admin action
#             admin_action = AdminAction(
#                 admin_id=str(current_user.id),
#                 action_type=ActionType.CREATE,
#                 target_collection="exam_category_structure",
#                 target_id=str(new_structure.id),
#                 changes={"action": "exam_structure_created"},
#             )
#             await admin_action.insert()

#             return {
#                 "message": "Exam category structure created successfully",
#                 "version": new_structure.version,
#                 "id": str(new_structure.id),
#             }

#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to create/update exam structure: {str(e)}",
#         )


# @router.get(
#     "/courses",
#     response_model=Dict[str, Any],
#     summary="Get exam categories with courses",
#     description="Get the exam categories structure with associated courses",
# )
# async def get_categories_with_courses():
#     """Get exam categories with their associated courses"""
#     try:
#         from ..models.course import Course

#         # Get the active structure
#         structure = await ExamCategoryStructure.find_one({"is_active": True})

#         if not structure:
#             return {
#                 "message": "No exam category structure found",
#                 "categories_with_courses": {},
#             }

#         # Get all active courses
#         all_courses = await Course.find({"is_active": True}).to_list()

#         # Organize courses by category and subcategory
#         categories_with_courses = {}

#         # Initialize structure with empty course lists
#         for category, subcategories in structure.structure.items():
#             categories_with_courses[category] = {}
#             for subcategory_group, subcategory_list in subcategories.items():
#                 categories_with_courses[category][subcategory_group] = {}
#                 for subcategory in subcategory_list:
#                     categories_with_courses[category][subcategory_group][
#                         subcategory
#                     ] = []

#         # Add courses to their respective categories
#         for course in all_courses:
#             category_value = course.category.value
#             sub_category = course.sub_category

#             # Find where this course belongs in the structure
#             for category, subcategories in structure.structure.items():
#                 if category.lower() == category_value.lower():
#                     for subcategory_group, subcategory_list in subcategories.items():
#                         if sub_category in subcategory_list:
#                             if (
#                                 subcategory_group
#                                 not in categories_with_courses[category]
#                             ):
#                                 categories_with_courses[category][
#                                     subcategory_group
#                                 ] = {}

#                             if (
#                                 sub_category
#                                 not in categories_with_courses[category][
#                                     subcategory_group
#                                 ]
#                             ):
#                                 categories_with_courses[category][subcategory_group][
#                                     sub_category
#                                 ] = []

#                             # Add course to the appropriate category
#                             categories_with_courses[category][subcategory_group][
#                                 sub_category
#                             ].append(
#                                 {
#                                     "id": str(course.id),
#                                     "title": course.title,
#                                     "code": course.code,
#                                     "thumbnail_url": course.thumbnail_url,
#                                     "price": course.price,
#                                     "is_free": course.is_free,
#                                     "discount_percent": course.discount_percent,
#                                     "enrolled_students_count": course.enrolled_students_count,
#                                 }
#                             )

#         return {
#             "message": "Exam categories with courses retrieved successfully",
#             "categories_with_courses": categories_with_courses,
#         }

#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to retrieve categories with courses: {str(e)}",
#         )
