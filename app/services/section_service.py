"""
Section service for course section management operations
"""

from typing import Dict, Any, List, Optional
from bson import ObjectId

from ..models.course import Course, Section
from ..models.question import Question
from ..models.admin_action import AdminAction, ActionType
from ..models.user import User
from .admin_service import AdminService


class SectionService:
    """Service class for course section management operations"""

    @staticmethod
    async def add_section_to_course(
        course_id: str, section_name: str, current_user: User, question_count: int = 10
    ) -> Dict[str, Any]:
        """
        Add a new section to a course

        Args:
            course_id: Course ID
            section_name: Name of the section to add
            current_user: User adding the section
            question_count: Number of questions to show in mock tests (default: 10)

        Returns:
            Dictionary with section addition result
        """
        # Validate course_id
        if not ObjectId.is_valid(course_id):
            raise ValueError("Invalid course ID format")

        # Get the course
        course = await Course.get(course_id)
        if not course:
            raise ValueError("Course not found")

        # Check if section already exists
        if course.get_section(section_name):
            raise ValueError("Section with this name already exists")

        # Create new section
        new_section = Section(
            name=section_name,
            description=f"Section: {section_name}",
            order=len(course.sections) + 1,
            question_count=question_count,
        )

        # Add section to course
        course.sections.append(new_section)
        course.update_timestamp()
        await course.save()

        # Log admin action
        await AdminService.log_admin_action(
            str(current_user.id),
            ActionType.CREATE,
            "courses",
            course_id,
            {
                "action": "section_added",
                "section_name": section_name,
            },
        )

        return {
            "message": f"Section '{section_name}' added successfully",
            "course_id": course_id,
            "section": {
                "name": new_section.name,
                "description": new_section.description,
                "order": new_section.order,
                "question_count": new_section.question_count,
            },
        }

    @staticmethod
    async def update_section_in_course(
        course_id: str, section_name: str, new_section_name: str, current_user: User
    ) -> Dict[str, Any]:
        """
        Update a section name in a course

        Args:
            course_id: Course ID
            section_name: Current section name
            new_section_name: New section name
            current_user: User updating the section

        Returns:
            Dictionary with section update result
        """
        # Validate course_id
        if not ObjectId.is_valid(course_id):
            raise ValueError("Invalid course ID format")

        # Get the course
        course = await Course.get(course_id)
        if not course:
            raise ValueError("Course not found")

        # Find the section
        section = course.get_section(section_name)
        if not section:
            raise ValueError(f"Section '{section_name}' not found")

        # Check if new name already exists
        if course.get_section(new_section_name):
            raise ValueError("Section with this name already exists")

        # Update section name
        old_name = section_name  # The section_name parameter is the old name

        if isinstance(course.sections[0], str):
            # Sections are stored as strings - find and replace
            for i, section in enumerate(course.sections):
                if section == old_name:
                    course.sections[i] = new_section_name
                    break
        else:
            # Sections are Section objects - update the object
            section.name = new_section_name
            section.description = f"Section: {new_section_name}"

        # Update questions in this section to use new section name
        await Question.find({"course_id": course_id, "section": old_name}).update_many(
            {"$set": {"section": new_section_name}}
        )

        course.update_timestamp()
        await course.save()

        # Log admin action
        await AdminService.log_admin_action(
            str(current_user.id),
            ActionType.UPDATE,
            "courses",
            course_id,
            {
                "action": "section_renamed",
                "old_name": old_name,
                "new_name": new_section_name,
            },
        )

        return {
            "message": f"Section renamed from '{old_name}' to '{new_section_name}' successfully",
            "course_id": course_id,
            "old_name": old_name,
            "new_name": new_section_name,
        }

    @staticmethod
    async def delete_section_from_course(
        course_id: str, section_name: str, current_user: User
    ) -> Dict[str, Any]:
        """
        Delete a section and all its questions from a course

        Args:
            course_id: Course ID
            section_name: Name of the section to delete
            current_user: User deleting the section

        Returns:
            Dictionary with section deletion result
        """
        # Validate course_id
        if not ObjectId.is_valid(course_id):
            raise ValueError("Invalid course ID format")

        # Get the course
        course = await Course.get(course_id)
        if not course:
            raise ValueError("Course not found")

        # Find the section
        section = course.get_section(section_name)
        if not section:
            raise ValueError(f"Section '{section_name}' not found")

        # Delete all questions in this section
        deleted_questions = await Question.find(
            {"course_id": course_id, "section": section_name}
        ).delete_many()

        # Remove section from course
        if isinstance(course.sections[0], str):
            # Sections are stored as strings
            course.sections = [s for s in course.sections if s != section_name]
        else:
            # Sections are Section objects
            course.sections = [s for s in course.sections if s.name != section_name]

        # Update order of remaining sections
        for i, remaining_section in enumerate(course.sections):
            remaining_section.order = i + 1

        course.update_timestamp()
        await course.save()

        # Log admin action
        await AdminService.log_admin_action(
            str(current_user.id),
            ActionType.DELETE,
            "courses",
            course_id,
            {
                "action": "section_deleted",
                "section_name": section_name,
                "deleted_questions_count": deleted_questions,
            },
        )

        return {
            "message": f"Section '{section_name}' and {deleted_questions} questions deleted successfully",
            "course_id": course_id,
            "deleted_questions_count": deleted_questions,
        }

    @staticmethod
    async def list_course_sections(course_id: str) -> Dict[str, Any]:
        """
        List all sections for a course

        Args:
            course_id: Course ID

        Returns:
            Dictionary with course sections
        """
        # Validate course_id
        if not ObjectId.is_valid(course_id):
            raise ValueError("Invalid course ID format")

        # Get the course
        course = await Course.get(course_id)
        if not course:
            raise ValueError("Course not found")

        # Get question counts for each section
        sections_with_counts = []
        for section in course.sections:
            question_count = await Question.find(
                {
                    "course_id": course_id,
                    "section": section.name,
                }
            ).count()

            sections_with_counts.append(
                {
                    "name": section.name,
                    "description": section.description,
                    "question_count": question_count,
                    "order": section.order,
                }
            )

        return {
            "message": f"Sections for course '{course.title}' retrieved successfully",
            "course": {
                "id": str(course.id),
                "title": course.title,
                "code": course.code,
            },
            "sections": sections_with_counts,
        }

    @staticmethod
    async def get_section_details(course_id: str, section_name: str) -> Dict[str, Any]:
        """
        Get details for a specific section in a course

        Args:
            course_id: Course ID
            section_name: Name of the section

        Returns:
            Dictionary with section details
        """
        # Validate course_id
        if not ObjectId.is_valid(course_id):
            raise ValueError("Invalid course ID format")

        # Get the course
        course = await Course.get(course_id)
        if not course:
            raise ValueError("Course not found")

        # Find the section
        section = course.get_section(section_name)
        if not section:
            raise ValueError(f"Section '{section_name}' not found in course")

        # Get question count for this section
        question_count = await Question.find(
            {
                "course_id": course_id,
                "section": section_name,
            }
        ).count()

        return {
            "message": f"Section '{section_name}' details retrieved successfully",
            "course": {
                "id": str(course.id),
                "title": course.title,
                "code": course.code,
            },
            "section": {
                "name": section.name,
                "description": section.description,
                "question_count": question_count,
                "order": section.order,
            },
        }

    @staticmethod
    async def update_section_question_count(
        course_id: str, section_name: str, new_count: int
    ) -> Dict[str, Any]:
        """
        Update question count for a section

        Args:
            course_id: Course ID
            section_name: Name of the section
            new_count: New question count

        Returns:
            Dictionary with update result
        """
        course = await Course.get(course_id)
        if not course:
            raise ValueError("Course not found")

        section = course.get_section(section_name)
        if not section:
            raise ValueError("Section not found")

        section.question_count = new_count
        await course.save()

        return {
            "message": "Question count updated",
            "section": {
                "name": section.name,
                "question_count": section.question_count,
            },
        }
