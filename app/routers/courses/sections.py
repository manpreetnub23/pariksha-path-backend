"""
Course sections router - focused on section management within courses
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query, Path
from typing import Optional, Dict, Any

from ...models.user import User
from ...dependencies import admin_required, get_current_user
from ...services.section_service import SectionService
from ...services.course_question_service import CourseQuestionService
from .schemas import (
    SectionCreateRequest,
    SectionUpdateRequest,
    QuestionCountUpdateRequest,
)
from fastapi import UploadFile, File, Form, Body

router = APIRouter(prefix="/api/v1/courses", tags=["Courses - Sections"])


@router.post(
    "/{course_id}/sections",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Add section to course",
    description="Admin endpoint to add a new section to a course",
)
async def add_section_to_course(
    course_id: str,
    section_data: SectionCreateRequest,
    current_user: User = Depends(admin_required),
):
    """Add a new section to a course (Admin only)"""
    try:
        result = await SectionService.add_section_to_course(
            course_id, section_data.section_name, current_user
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add section: {str(e)}",
        )


@router.put(
    "/{course_id}/sections/{section_name}",
    response_model=Dict[str, Any],
    summary="Update section name",
    description="Admin endpoint to rename a section in a course",
)
async def update_section_in_course(
    course_id: str,
    section_name: str,
    section_data: SectionUpdateRequest,
    current_user: User = Depends(admin_required),
):
    """Update a section name in a course (Admin only)"""
    try:
        result = await SectionService.update_section_in_course(
            course_id, section_name, section_data.new_section_name, current_user
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update section: {str(e)}",
        )


@router.delete(
    "/{course_id}/sections/{section_name}",
    response_model=Dict[str, Any],
    summary="Delete section from course",
    description="Admin endpoint to delete a section and all its questions from a course",
)
async def delete_section_from_course(
    course_id: str,
    section_name: str,
    current_user: User = Depends(admin_required),
):
    """Delete a section and all its questions from a course (Admin only)"""
    try:
        result = await SectionService.delete_section_from_course(
            course_id, section_name, current_user
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete section: {str(e)}",
        )


@router.get(
    "/{course_id}/sections",
    response_model=Dict[str, Any],
    summary="List course sections",
    description="Get all sections for a specific course",
)
async def list_course_sections(
    course_id: str,
    current_user: Optional[User] = Depends(get_current_user),
):
    """List all sections for a course"""
    try:
        result = await SectionService.list_course_sections(course_id)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve course sections: {str(e)}",
        )


@router.get(
    "/{course_id}/sections/{section_name}",
    response_model=Dict[str, Any],
    summary="Get section details",
    description="Get details about a specific section in a course",
)
async def get_section_details(
    course_id: str,
    section_name: str,
    current_user: Optional[User] = Depends(get_current_user),
):
    """Get details for a specific section in a course"""
    try:
        result = await SectionService.get_section_details(course_id, section_name)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve section details: {str(e)}",
        )


@router.put(
    "/{course_id}/sections/{section_name}/question-count",
    response_model=Dict[str, Any],
    summary="Update section question count",
    description="Update the question count for a section",
)
async def update_section_question_count(
    course_id: str,
    section_name: str,
    new_count: int = Body(..., embed=True),
):
    """Update question count for a section"""
    try:
        result = await SectionService.update_section_question_count(
            course_id, section_name, new_count
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update question count: {str(e)}",
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
        contents = await file.read()
        result = await CourseQuestionService.upload_questions_to_section(
            course_id, section, contents, current_user
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload questions: {str(e)}",
        )


@router.get(
    "/{course_id}/sections/{section_name}/questions",
    response_model=Dict[str, Any],
    summary="Get questions for course section",
    description="Get all questions for a specific section in a course or random mock questions",
)
async def get_section_questions(
    course_id: str,
    section_name: str,
    page: int = Query(1, description="Page number", ge=1),
    limit: int = Query(10, description="Items per page", ge=1, le=100),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty"),
    topic: Optional[str] = Query(None, description="Filter by topic"),
    mode: Optional[str] = Query(None, description="Mode: normal | mock"),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    Get questions for a specific section in a course.
    - `mode=normal` (default): Paginated, filtered results.
    - `mode=mock`: Fetch random N questions based on section.question_count.
    """
    try:
        result = await CourseQuestionService.get_section_questions(
            course_id=course_id,
            section_name=section_name,
            page=page,
            limit=limit,
            difficulty=difficulty,
            topic=topic,
            mode=mode,
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve section questions: {str(e)}",
        )
