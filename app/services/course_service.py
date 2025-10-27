"""
Course service for course management operations
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from bson import ObjectId

from ..models.course import Course, Section
from ..models.question import Question, QuestionType, DifficultyLevel, QuestionOption
from ..models.admin_action import AdminAction, ActionType
from ..models.user import User
from ..models.course_enrollment import CourseEnrollment
from ..models.enums import ExamCategory
from .admin_service import AdminService


class CourseService:
    """Service class for course management operations"""

    @staticmethod
    async def create_course(
        course_data: Dict[str, Any], current_user: User
    ) -> Dict[str, Any]:
        """
        Create a new course

        Args:
            course_data: Course data dictionary
            current_user: User creating the course

        Returns:
            Dictionary with course creation result
        """
        # Check if course code already exists
        existing_course = await Course.find_one({"code": course_data["code"]})
        if existing_course:
            raise ValueError("Course with this code already exists")

        # Convert string sections to Section objects
        section_objects = []
        for i, section_name in enumerate(course_data.get("sections", [])):
            section_objects.append(
                Section(
                    name=section_name,
                    description=f"Section {i + 1}: {section_name}",
                    order=i + 1,
                    question_count=0,
                )
            )

        # Create new course
        new_course = Course(
            title=course_data["title"],
            code=course_data["code"],
            category=course_data["category"],
            sub_category=course_data["sub_category"],
            description=course_data["description"],
            sections=section_objects,
            price=course_data["price"],
            is_free=course_data["is_free"],
            discount_percent=course_data.get("discount_percent"),
            validity_period_days=course_data.get("validity_period_days", 365),
            mock_test_timer_seconds=course_data.get("mock_test_timer_seconds", 3600),
            material_ids=course_data.get("material_ids", []),
            test_series_ids=course_data.get("test_series_ids", []),
            thumbnail_url=course_data["thumbnail_url"],
            icon_url=course_data.get("icon_url"),
            priority_order=course_data.get("priority_order", 0),
            banner_url=course_data.get("banner_url"),
            tagline=course_data.get("tagline"),
            created_by=str(current_user.id),
        )

        await new_course.insert()

        # Log admin action
        await AdminService.log_admin_action(
            str(current_user.id),
            ActionType.CREATE,
            "courses",
            str(new_course.id),
            {"action": "course_created"},
        )

        return {
            "message": "Course created successfully",
            "course_id": str(new_course.id),
        }

    @staticmethod
    async def list_courses(
        category: Optional[ExamCategory] = None,
        search: Optional[str] = None,
        section: Optional[str] = None,
        is_free: Optional[bool] = None,
        is_active: Optional[bool] = None,
        sort_by: str = "priority_order",
        sort_order: str = "asc",
        page: int = 1,
        limit: int = 10,
        current_user: Optional[User] = None,
    ) -> Dict[str, Any]:
        """
        List courses with filtering and pagination

        Args:
            category: Filter by exam category
            search: Search in title and description
            section: Filter by section
            is_free: Filter by free courses
            is_active: Filter by active status
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)
            page: Page number
            limit: Items per page
            current_user: Current user (for access control)

        Returns:
            Dictionary with courses and pagination info
        """
        # Build query filters
        query_filters = {}

        # Always filter by is_active=True for non-admin users
        if current_user is None or current_user.role != "admin":
            query_filters["is_active"] = True
        elif is_active is not None:
            query_filters["is_active"] = is_active

        if category:
            query_filters["category"] = category

        if section:
            query_filters["sections"] = {"$in": [section]}

        if is_free is not None:
            query_filters["is_free"] = is_free

        if search:
            # Search in title or description
            query_filters["$or"] = [
                {"title": {"$regex": search, "$options": "i"}},
                {"description": {"$regex": search, "$options": "i"}},
            ]

        # Calculate pagination
        skip = (page - 1) * limit

        # Set sort order with secondary sort for consistent category ordering across auth states
        sort_direction = 1 if sort_order == "asc" else -1
        
        # Primary sort by priority_order, secondary sort by category for consistent ordering
        sort_criteria = [("priority_order", sort_direction), ("category", 1), ("title", 1)]

        # Fetch courses with improved sorting for consistent category ordering
        courses = (
            await Course.find(query_filters)
            .sort(sort_criteria)
            .skip(skip)
            .limit(limit)
            .to_list()
        )

        # Count total matching courses for pagination info
        total_courses = await Course.find(query_filters).count()
        total_pages = (total_courses + limit - 1) // limit

        # Convert course objects to response format
        course_responses = []
        for course in courses:
            course_data = {
                "id": str(course.id),
                "title": course.title,
                "code": course.code,
                "category": course.category.value,
                "sub_category": course.sub_category,
                "description": course.description,
                "sections": course.sections,
                "price": course.price,
                "is_free": course.is_free,
                "discount_percent": course.discount_percent,
                "validity_period_days": getattr(course, "validity_period_days", 365),
                "thumbnail_url": course.thumbnail_url,
                "icon_url": getattr(course, "icon_url", None),
                "banner_url": getattr(course, "banner_url", None),
                "mock_test_timer_seconds": getattr(course, "mock_test_timer_seconds", 3600),
                "material_ids": course.material_ids,
            }
            course_responses.append(course_data)

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

    @staticmethod
    async def get_course(course_id: str) -> Dict[str, Any]:
        """
        Get course details by ID

        Args:
            course_id: Course ID

        Returns:
            Dictionary with course details
        """
        course = await Course.get(course_id)
        if not course:
            raise ValueError("Course not found")

        # Convert Section objects to strings for response
        sections_list = course.get_section_names()

        return {
            "message": "Course retrieved successfully",
            "course": {
                "id": str(course.id),
                "title": course.title,
                "code": course.code,
                "category": course.category.value,
                "sub_category": course.sub_category,
                "description": course.description,
                "sections": sections_list,
                "price": course.price,
                "is_free": course.is_free,
                "discount_percent": course.discount_percent,
                "validity_period_days": getattr(course, "validity_period_days", 365),
                "mock_test_timer_seconds": getattr(course, "mock_test_timer_seconds", 3600),
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

    @staticmethod
    async def update_course(
        course_id: str, course_data: Dict[str, Any], current_user: User
    ) -> Dict[str, Any]:
        """
        Update course details

        Args:
            course_id: Course ID
            course_data: Course update data
            current_user: User updating the course

        Returns:
            Dictionary with update result
        """
        course = await Course.get(course_id)
        if not course:
            raise ValueError("Course not found")

        # Track changes for audit log
        changes = {}

        # Update fields if provided
        for field, value in course_data.items():
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
            await AdminService.log_admin_action(
                str(current_user.id),
                ActionType.UPDATE,
                "courses",
                course_id,
                changes,
            )
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

    @staticmethod
    async def delete_course(course_id: str, current_user: User) -> Dict[str, Any]:
        """
        Delete (deactivate) a course

        Args:
            course_id: Course ID
            current_user: User deleting the course

        Returns:
            Dictionary with deletion result
        """
        course = await Course.get(course_id)
        if not course:
            raise ValueError("Course not found")

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
        await AdminService.log_admin_action(
            str(current_user.id),
            ActionType.DELETE,
            "courses",
            course_id,
            {"is_active": False},
        )

        return {
            "message": "Course deactivated successfully",
            "course_id": course_id,
        }

    @staticmethod
    async def enroll_user_in_course(
        course_id: str, current_user: User
    ) -> Dict[str, Any]:
        """
        Enroll user in a course

        Args:
            course_id: Course ID
            current_user: User enrolling in the course

        Returns:
            Dictionary with enrollment result
        """
        course = await Course.get(course_id)
        if not course:
            raise ValueError("Course not found")

        if not course.is_active:
            raise ValueError("This course is currently not available")

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

                # Create course enrollment record
                expires_at = datetime.now() + timedelta(
                    days=course.validity_period_days
                )
                enrollment = CourseEnrollment(
                    user_id=str(current_user.id),
                    course_id=course_id,
                    expires_at=expires_at,
                    enrollment_source="free_enrollment",
                )
                await enrollment.insert()

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

                    # Create course enrollment record
                    expires_at = datetime.now() + timedelta(
                        days=course.validity_period_days
                    )
                    enrollment = CourseEnrollment(
                        user_id=str(current_user.id),
                        course_id=course_id,
                        expires_at=expires_at,
                        enrollment_source="premium_access",
                    )
                    await enrollment.insert()

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

    @staticmethod
    async def get_enrolled_courses(current_user: User) -> Dict[str, Any]:
        """
        Get courses the current user is enrolled in

        Args:
            current_user: Current user

        Returns:
            Dictionary with enrolled courses
        """
        # Initialize empty list if enrolled_courses is None
        enrolled_course_ids = current_user.enrolled_courses or []

        if not enrolled_course_ids:
            return {
                "message": "You are not enrolled in any courses",
                "courses": [],
            }

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
        course_responses = []
        for course in courses:
            # Convert Section objects to strings for response
            sections_list = course.get_section_names()

            course_responses.append(
                {
                    "id": str(course.id),
                    "title": course.title,
                    "code": course.code,
                    "category": course.category.value,
                    "sub_category": course.sub_category,
                    "description": course.description,
                    "sections": sections_list,
                    "thumbnail_url": course.thumbnail_url,
                    "icon_url": course.icon_url,
                    "material_ids": course.material_ids,
                    "test_series_ids": course.test_series_ids,
                }
            )

        return {
            "message": "Enrolled courses retrieved successfully",
            "courses": course_responses,
        }
