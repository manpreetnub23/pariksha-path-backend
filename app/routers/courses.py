from datetime import datetime, timezone
from fastapi import (
    APIRouter,
    HTTPException,
    Depends,
    status,
    Query,
    UploadFile,
    File,
    Form,
)
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
import csv
import io
from datetime import datetime
from bson import ObjectId

from ..models.course import Course, ExamSubCategory
from ..models.question import Question
from ..models.admin_action import AdminAction, ActionType
from ..models.user import User
from ..models.enums import ExamCategory
from ..dependencies import admin_required, get_current_user

router = APIRouter(prefix="/api/v1/courses", tags=["Courses"])

# A course is an exam for all intents and purposes.


# Request/Response Models
class CourseCreateRequest(BaseModel):
    title: str
    code: str
    category: ExamCategory
    sub_category: str
    description: str
    price: float
    is_free: bool = False
    discount_percent: Optional[float] = None
    material_ids: List[str] = []
    test_series_ids: List[str] = []
    thumbnail_url: str
    icon_url: Optional[str] = None
    priority_order: int = 0
    banner_url: Optional[str] = None
    tagline: Optional[str] = None
    sections: List[str] = []

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Complete JEE Main Physics",
                "code": "JEE-PHY-001",
                "category": "engineering",
                "sub_category": "JEE Main",
                "description": "Comprehensive course for JEE Main Physics preparation",
                "price": 4999.0,
                "is_free": False,
                "discount_percent": 10.0,
                "material_ids": [],
                "test_series_ids": [],
                "thumbnail_url": "https://example.com/images/jee-physics.jpg",
                "icon_url": "https://example.com/icons/physics.png",
                "priority_order": 1,
                "banner_url": "https://example.com/banners/jee-physics-banner.jpg",
                "tagline": "Master Physics concepts for JEE Main",
                "sections": ["Physics", "Chemistry", "Biology"],
            }
        }


class CourseUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    sections: Optional[List[str]] = None
    price: Optional[float] = None
    is_free: Optional[bool] = None
    discount_percent: Optional[float] = None
    material_ids: Optional[List[str]] = None
    test_series_ids: Optional[List[str]] = None
    thumbnail_url: Optional[str] = None
    icon_url: Optional[str] = None
    priority_order: Optional[int] = None
    banner_url: Optional[str] = None
    tagline: Optional[str] = None
    is_active: Optional[bool] = None


class CourseResponse(BaseModel):
    id: str
    title: str
    code: str
    category: str
    sub_category: str
    description: str
    sections: Optional[List[str]] = None
    price: float
    is_free: bool
    discount_percent: Optional[float] = None
    material_ids: List[str]
    test_series_ids: List[str]
    enrolled_students_count: int
    thumbnail_url: str
    icon_url: Optional[str] = None
    banner_url: Optional[str] = None
    tagline: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


# Test endpoint to check if the router is working
@router.get("/test")
async def test_endpoint():
    """Test endpoint to verify the router is working"""
    return {"message": "Courses router is working", "status": "success"}


# Endpoint for admins to create courses
@router.post(
    "/",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new course",
    description="Admin endpoint to create a new course",
)
async def create_course(
    course_data: CourseCreateRequest, current_user: User = Depends(admin_required)
):
    """Create a new course (Admin only)"""
    try:
        print(f"Creating course with data: {course_data.dict()}")
        print(f"Current user: {current_user.email if current_user else 'None'}")

        # Check if course code already exists
        existing_course = await Course.find_one({"code": course_data.code})
        if existing_course:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Course with this code already exists",
            )

        # Create new course
        new_course = Course(
            title=course_data.title,
            code=course_data.code,
            category=course_data.category,
            sub_category=course_data.sub_category,
            description=course_data.description,
            sections=course_data.sections,
            price=course_data.price,
            is_free=course_data.is_free,
            discount_percent=course_data.discount_percent,
            material_ids=course_data.material_ids,
            test_series_ids=course_data.test_series_ids,
            thumbnail_url=course_data.thumbnail_url,
            icon_url=course_data.icon_url,
            priority_order=course_data.priority_order,
            banner_url=course_data.banner_url,
            tagline=course_data.tagline,
            created_by=str(current_user.id),
        )

        await new_course.insert()

        # Log admin action
        admin_action = AdminAction(
            admin_id=str(current_user.id),
            action_type=ActionType.CREATE,
            target_collection="courses",
            target_id=str(new_course.id),
            changes={"action": "course_created"},
        )
        await admin_action.insert()

        return {
            "message": "Course created successfully",
            "course_id": str(new_course.id),
        }

    except HTTPException as e:
        print(f"HTTPException in create_course: {e.detail}")
        raise e
    except Exception as e:
        print(f"Exception in create_course: {str(e)}")
        print(f"Exception type: {type(e)}")
        import traceback

        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create course: {str(e)}",
        )


# Endpoint to get all courses (public)
@router.get(
    "/",
    response_model=Dict[str, Any],
    summary="List all courses",
    description="Get a paginated list of all available courses with optional filters",
)
async def list_courses(
    category: Optional[ExamCategory] = Query(
        None, description="Filter by exam category"
    ),
    search: Optional[str] = Query(None, description="Search in title and description"),
    section: Optional[str] = Query(None, description="Filter by section"),
    is_free: Optional[bool] = Query(None, description="Filter by free courses"),
    is_active: Optional[bool] = Query(True, description="Filter by active status"),
    sort_by: str = Query("priority_order", description="Field to sort by"),
    sort_order: str = Query("asc", description="Sort order (asc or desc)"),
    page: int = Query(1, description="Page number", ge=1),
    limit: int = Query(10, description="Items per page", ge=1, le=100),
    current_user: Optional[User] = Depends(get_current_user),
):
    """List all courses with filters and pagination"""
    try:
        print("🔍 DEBUG: list_courses endpoint called")
        print(f"🔍 DEBUG: current_user = {current_user}")

        # Build query filters
        query_filters = {}

        # Always filter by is_active=True for non-admin users
        if current_user is None or current_user.role != "admin":
            query_filters["is_active"] = True
            print("🔍 DEBUG: Using is_active=True filter (non-admin user)")
        elif is_active is not None:
            query_filters["is_active"] = is_active
            print(f"🔍 DEBUG: Using is_active={is_active} filter (admin user)")

        if category:
            query_filters["category"] = category
            print(f"🔍 DEBUG: Added category filter: {category}")

        if section:
            query_filters["sections"] = {"$in": [section]}
            print(f"🔍 DEBUG: Added section filter: {section}")

        if is_free is not None:
            query_filters["is_free"] = is_free
            print(f"🔍 DEBUG: Added is_free filter: {is_free}")

        if search:
            # Search in title or description
            query_filters["$or"] = [
                {"title": {"$regex": search, "$options": "i"}},
                {"description": {"$regex": search, "$options": "i"}},
            ]
            print(f"🔍 DEBUG: Added search filter: {search}")

        # Calculate pagination
        skip = (page - 1) * limit
        print(f"🔍 DEBUG: Pagination: page={page}, limit={limit}, skip={skip}")

        # Set sort order
        sort_direction = 1 if sort_order == "asc" else -1
        print(f"🔍 DEBUG: Sorting by {sort_by} in {sort_order} order")

        print(f"🔍 DEBUG: Final query filters: {query_filters}")

        try:
            # Fetch courses
            print("🔍 DEBUG: Fetching courses from database...")
            courses = (
                await Course.find(query_filters)
                .sort([(sort_by, sort_direction)])
                .skip(skip)
                .limit(limit)
                .to_list()
            )
            print(f"🔍 DEBUG: Found {len(courses)} courses")

            # Count total matching courses for pagination info
            print("🔍 DEBUG: Counting total courses...")
            total_courses = await Course.find(query_filters).count()
            total_pages = (total_courses + limit - 1) // limit
            print(
                f"🔍 DEBUG: Total courses: {total_courses}, Total pages: {total_pages}"
            )

            # Convert course objects to response format
            print("🔍 DEBUG: Converting course objects to response format...")
            course_responses = []

            for course in courses:
                try:
                    course_data = {
                        "id": str(course.id),
                        "title": course.title,
                        "code": course.code,
                        "category": course.category.value,
                        "sub_category": course.sub_category,
                        "description": course.description,
                        "sections": getattr(course, "sections", []),
                        "price": course.price,
                        "is_free": course.is_free,
                        "discount_percent": course.discount_percent,
                        "thumbnail_url": course.thumbnail_url,
                        "icon_url": getattr(course, "icon_url", None),
                        "banner_url": getattr(course, "banner_url", None),
                        "tagline": getattr(course, "tagline", None),
                        "enrolled_students_count": getattr(
                            course, "enrolled_students_count", 0
                        ),
                        "is_active": course.is_active,
                        "created_at": course.created_at,
                    }
                    course_responses.append(course_data)
                except Exception as e:
                    print(f"🔍 DEBUG: Error processing course {course.id}: {str(e)}")
                    import traceback

                    print(f"🔍 DEBUG: {traceback.format_exc()}")

            print("🔍 DEBUG: Successfully created response")

            return {
                "message": "Courses retrieved successfully",
                "data": course_responses,
                "pagination": {
                    "total": total_courses,
                    "page": page,
                    "limit": limit,
                    "total_pages": total_pages,
                },
            }

        except Exception as e:
            print(f"🔍 DEBUG: Error in database operations: {str(e)}")
            import traceback

            print(f"🔍 DEBUG: {traceback.format_exc()}")
            raise

    except Exception as e:
        print(f"🔍 DEBUG: Unhandled exception in list_courses: {str(e)}")
        import traceback

        print(f"🔍 DEBUG: {traceback.format_exc()}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve courses: {str(e)}",
        )


# Endpoint to get enrolled courses for current user
@router.get(
    "/enrolled",
    response_model=Dict[str, Any],
    summary="Get enrolled courses",
    description="Get all courses the current user is enrolled in",
)
async def get_enrolled_courses(current_user: User = Depends(get_current_user)):
    """Get courses the current user is enrolled in"""
    try:
        # Initialize empty list if enrolled_courses is None
        enrolled_course_ids = current_user.enrolled_courses or []

        if not enrolled_course_ids:
            return {
                "message": "You are not enrolled in any courses",
                "courses": [],
            }

        # Fetch all enrolled courses - Convert string IDs to ObjectIds
        from bson import ObjectId

        # Convert string IDs to ObjectIds for the database query
        object_ids = []
        for course_id in enrolled_course_ids:
            try:
                object_ids.append(ObjectId(course_id))
            except Exception as e:
                print(f"Invalid ObjectId: {course_id}, error: {e}")
                continue

        if not object_ids:
            return {
                "message": "No valid course IDs found",
                "courses": [],
            }

        courses = await Course.find(
            {"_id": {"$in": object_ids}, "is_active": True}
        ).to_list()

        # Convert course objects to response format
        course_responses = [
            {
                "id": str(course.id),
                "title": course.title,
                "code": course.code,
                "category": course.category.value,
                "sub_category": course.sub_category,
                "description": course.description,
                "sections": getattr(course, "sections", []),
                "thumbnail_url": course.thumbnail_url,
                "icon_url": course.icon_url,
                "material_ids": course.material_ids,
                "test_series_ids": course.test_series_ids,
            }
            for course in courses
        ]

        return {
            "message": "Enrolled courses retrieved successfully",
            "courses": course_responses,
        }

    except Exception as e:
        print(f"Error in get_enrolled_courses: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve enrolled courses: {str(e)}",
        )


# Endpoint to get course by ID (public)
@router.get(
    "/{course_id}",
    response_model=Dict[str, Any],
    summary="Get course details",
    description="Get detailed information about a specific course",
)
async def get_course(course_id: str):
    """Get course details by ID"""
    try:
        course = await Course.get(course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found",
            )

        # For inactive courses, only admins should be able to view them
        # This is handled in the frontend by checking user role

        return {
            "message": "Course retrieved successfully",
            "course": {
                "id": str(course.id),
                "title": course.title,
                "code": course.code,
                "category": course.category.value,
                "sub_category": course.sub_category,
                "description": course.description,
                "sections": getattr(course, "sections", []),
                "price": course.price,
                "is_free": course.is_free,
                "discount_percent": course.discount_percent,
                "material_ids": course.material_ids,
                "test_series_ids": course.test_series_ids,
                "thumbnail_url": course.thumbnail_url,
                "icon_url": course.icon_url,
                "banner_url": course.banner_url,
                "tagline": course.tagline,
                "enrolled_students_count": course.enrolled_students_count,
                "is_active": course.is_active,
                "created_at": course.created_at,
                "updated_at": course.updated_at,
            },
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve course: {str(e)}",
        )


# Endpoint to update course (admin only)
@router.put(
    "/{course_id}",
    response_model=Dict[str, Any],
    summary="Update course",
    description="Admin endpoint to update course details",
)
async def update_course(
    course_id: str,
    course_data: CourseUpdateRequest,
    current_user: User = Depends(admin_required),
):
    """Update course details (Admin only)"""
    try:
        course = await Course.get(course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found",
            )

        # Track changes for audit log
        changes = {}

        # Update fields if provided
        for field, value in course_data.dict(exclude_unset=True).items():
            if value is not None:
                setattr(course, field, value)
                changes[field] = (
                    str(value) if not isinstance(value, list) else "updated"
                )

        # Only update if there are changes
        if changes:
            course.update_timestamp()
            await course.save()

            # Log admin action
            admin_action = AdminAction(
                admin_id=str(current_user.id),
                action_type=ActionType.UPDATE,
                target_collection="courses",
                target_id=course_id,
                changes=changes,
            )
            await admin_action.insert()

            return {
                "message": "Course updated successfully",
                "course_id": course_id,
                "changes": changes,
            }
        else:
            return {
                "message": "No changes to apply",
                "course_id": course_id,
            }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update course: {str(e)}",
        )


# Endpoint to delete course (admin only - soft delete)
@router.delete(
    "/{course_id}",
    response_model=Dict[str, Any],
    summary="Delete course",
    description="Admin endpoint to delete (deactivate) a course",
)
async def delete_course(course_id: str, current_user: User = Depends(admin_required)):
    """Delete (deactivate) a course (Admin only)"""
    try:
        course = await Course.get(course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found",
            )

        # Check if course is already inactive
        if not course.is_active:
            return {
                "message": "Course is already deactivated",
                "course_id": course_id,
            }

        # Soft delete by setting is_active=False
        course.is_active = False
        course.update_timestamp()
        await course.save()

        # Log admin action
        admin_action = AdminAction(
            admin_id=str(current_user.id),
            action_type=ActionType.DELETE,
            target_collection="courses",
            target_id=course_id,
            changes={"is_active": False},
        )
        await admin_action.insert()

        return {
            "message": "Course deactivated successfully",
            "course_id": course_id,
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete course: {str(e)}",
        )


# Endpoint to enroll in a course (for students)
@router.post(
    "/{course_id}/enroll",
    response_model=Dict[str, Any],
    summary="Enroll in course",
    description="Student endpoint to enroll in a course",
)
async def enroll_in_course(
    course_id: str,
    current_user: User = Depends(get_current_user),
):
    """Enroll in a course (Student only)"""
    try:
        course = await Course.get(course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found",
            )

        if not course.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This course is currently not available",
            )

        # Check if already enrolled
        if course_id in current_user.enrolled_courses:
            return {
                "message": "You are already enrolled in this course",
                "course_id": course_id,
                "course_title": course.title,
            }

        # For free courses, enroll directly
        if course.is_free:
            # Add course to user's enrolled courses
            if course_id not in current_user.enrolled_courses:
                current_user.enrolled_courses.append(course_id)
                current_user.update_timestamp()
                await current_user.save()

                # Increment enrolled students count
                course.enrolled_students_count += 1
                course.update_timestamp()
                await course.save()

                return {
                    "message": "Successfully enrolled in free course",
                    "course_id": course_id,
                    "course_title": course.title,
                }
        else:
            # For paid courses, check if the user has premium access or has purchased this course
            if current_user.has_premium_access:
                # Premium users can access all courses
                if course_id not in current_user.enrolled_courses:
                    current_user.enrolled_courses.append(course_id)
                    current_user.update_timestamp()
                    await current_user.save()

                    # Increment enrolled students count
                    course.enrolled_students_count += 1
                    course.update_timestamp()
                    await course.save()

                    return {
                        "message": "Successfully enrolled with premium access",
                        "course_id": course_id,
                        "course_title": course.title,
                    }
            else:
                # Redirect to payment flow for non-premium users
                # The actual enrollment will happen after payment confirmation
                price = course.price
                if course.discount_percent:
                    discount_amount = (course.price * course.discount_percent) / 100
                    price = course.price - discount_amount

                return {
                    "message": "Payment required to enroll in this course",
                    "course_id": course_id,
                    "course_title": course.title,
                    "price": price,
                    "original_price": course.price,
                    "discount_percent": course.discount_percent,
                    "requires_payment": True,
                }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enroll in course: {str(e)}",
        )


# Endpoint to add material to a course (admin only)
@router.post(
    "/{course_id}/materials",
    response_model=Dict[str, Any],
    summary="Add material to course",
    description="Admin endpoint to add study material to a course",
)
async def add_material_to_course(
    course_id: str,
    data: Dict[str, Any],
    current_user: User = Depends(admin_required),
):
    """Add study material to a course (Admin only)"""
    try:
        course = await Course.get(course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found",
            )

        material_id = data.get("material_id")
        if not material_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Material ID is required",
            )

        # Check if material ID already exists in the course
        if material_id in course.material_ids:
            return {
                "message": "Material already added to this course",
                "course_id": course_id,
                "material_id": material_id,
            }

        # Add material to course
        course.material_ids.append(material_id)
        course.update_timestamp()
        await course.save()

        # Log admin action
        admin_action = AdminAction(
            admin_id=str(current_user.id),
            action_type=ActionType.UPDATE,
            target_collection="courses",
            target_id=course_id,
            changes={"action": "material_added", "material_id": material_id},
        )
        await admin_action.insert()

        return {
            "message": "Material added to course successfully",
            "course_id": course_id,
            "material_id": material_id,
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add material to course: {str(e)}",
        )


# Endpoint to add test series to a course (admin only)
@router.post(
    "/{course_id}/test-series",
    response_model=Dict[str, Any],
    summary="Add test series to course",
    description="Admin endpoint to add test series to a course",
)
async def add_test_series_to_course(
    course_id: str,
    data: Dict[str, Any],
    current_user: User = Depends(admin_required),
):
    """Add test series to a course (Admin only)"""
    try:
        course = await Course.get(course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found",
            )

        test_series_id = data.get("test_series_id")
        if not test_series_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Test series ID is required",
            )

        # Check if test series ID already exists in the course
        if test_series_id in course.test_series_ids:
            return {
                "message": "Test series already added to this course",
                "course_id": course_id,
                "test_series_id": test_series_id,
            }

        # Add test series to course
        course.test_series_ids.append(test_series_id)
        course.update_timestamp()
        await course.save()

        # Log admin action
        admin_action = AdminAction(
            admin_id=str(current_user.id),
            action_type=ActionType.UPDATE,
            target_collection="courses",
            target_id=course_id,
            changes={"action": "test_series_added", "test_series_id": test_series_id},
        )
        await admin_action.insert()

        return {
            "message": "Test series added to course successfully",
            "course_id": course_id,
            "test_series_id": test_series_id,
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add test series to course: {str(e)}",
        )


# Endpoint to remove material from a course (admin only)
@router.delete(
    "/{course_id}/materials/{material_id}",
    response_model=Dict[str, Any],
    summary="Remove material from course",
    description="Admin endpoint to remove study material from a course",
)
async def remove_material_from_course(
    course_id: str,
    material_id: str,
    current_user: User = Depends(admin_required),
):
    """Remove study material from a course (Admin only)"""
    try:
        course = await Course.get(course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found",
            )

        # Check if material exists in course
        if material_id not in course.material_ids:
            return {
                "message": "Material not found in this course",
                "course_id": course_id,
                "material_id": material_id,
            }

        # Remove material from course
        course.material_ids.remove(material_id)
        course.update_timestamp()
        await course.save()

        # Log admin action
        admin_action = AdminAction(
            admin_id=str(current_user.id),
            action_type=ActionType.UPDATE,
            target_collection="courses",
            target_id=course_id,
            changes={"action": "material_removed", "material_id": material_id},
        )
        await admin_action.insert()

        return {
            "message": "Material removed from course successfully",
            "course_id": course_id,
            "material_id": material_id,
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove material from course: {str(e)}",
        )


# Endpoint to remove test series from a course (admin only)
@router.delete(
    "/{course_id}/test-series/{test_series_id}",
    response_model=Dict[str, Any],
    summary="Remove test series from course",
    description="Admin endpoint to remove a test series from a course",
)
async def remove_test_series_from_course(
    course_id: str,
    test_series_id: str,
    current_user: User = Depends(admin_required),
):
    """Remove test series from a course (Admin only)"""
    try:
        # Validate course_id format
        if not ObjectId.is_valid(course_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid course ID format",
            )

        # Find the course
        course = await Course.get(course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
            )

        # Remove test series ID if it exists
        if test_series_id in course.test_series_ids:
            course.test_series_ids.remove(test_series_id)
            await course.save()

        # Log admin action
        admin_action = AdminAction(
            admin_id=str(current_user.id),
            action_type=ActionType.UPDATE,
            target_collection="courses",
            target_id=course_id,
            changes={"action": "test_series_removed", "test_series_id": test_series_id},
        )
        await admin_action.insert()

        return {"status": "success", "message": "Test series removed from course"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove test series from course: {str(e)}",
        )


@router.post(
    "/upload-questions",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Upload questions to a course section",
    description="Upload questions to a specific section in a course via CSV",
)
async def upload_questions_to_section(
    file: UploadFile = File(...),
    course_id: str = Form(...),
    section: str = Form(...),
    current_user: User = Depends(admin_required),
):
    """Upload questions to a specific section in a course"""
    try:
        # Validate course_id
        if not ObjectId.is_valid(course_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid course ID format",
            )

        # Get the course
        course = await Course.get(course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
            )

        # Validate section exists in course
        if not course.sections or section not in course.sections:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Section '{section}' not found in course",
            )

        # Read and parse CSV file
        contents = await file.read()
        text = contents.decode("utf-8")
        csv_reader = csv.DictReader(io.StringIO(text))

        questions = []
        for row in csv_reader:
            try:
                # Extract options, filtering out empty ones
                options = []
                for opt in [
                    row.get("option_a", ""),
                    row.get("option_b", ""),
                    row.get("option_c", ""),
                    row.get("option_d", ""),
                ]:
                    if opt and str(opt).strip():
                        options.append(str(opt).strip())

                # Map CSV row to Question model
                question = Question(
                    question_text=row.get("question", "").strip(),
                    options=options,
                    correct_answers=[row.get("correct_answer", "").strip()],
                    explanation=row.get("explanation", "").strip(),
                    difficulty="medium",  # Default difficulty
                    tags=[],  # No tags in the new format
                    course_id=course_id,
                    section=section,
                    question_type="single_choice",  # Default to single choice
                    marks=float(row.get("marks", 1.0)),
                    created_by=str(current_user.id),
                    updated_at=datetime.utcnow(),
                    remarks=row.get("remarks", "").strip(),
                )
                questions.append(question)
            except Exception as e:
                print(f"Error processing row: {row}. Error: {str(e)}")
                continue

        # Save questions to database
        if questions:
            await Question.insert_many(questions)

        # Log admin action
        admin_action = AdminAction(
            admin_id=str(current_user.id),
            action_type=ActionType.CREATE,
            target_collection="questions",
            target_id=course_id,
            changes={
                "action": "questions_uploaded",
                "count": len(questions),
                "section": section,
            },
        )
        await admin_action.insert()

        return {
            "status": "success",
            "message": f"Successfully uploaded {len(questions)} questions to section '{section}'",
            "count": len(questions),
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in upload_questions_to_section: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload questions: {str(e)}",
        )
