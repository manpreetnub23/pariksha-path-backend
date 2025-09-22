"""
Admin section file management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import Dict, Any, List
from bson import ObjectId

from ...models.user import User
from ...models.course import Course, SectionFile
from ...dependencies import admin_required
from ...services.file_upload_service import FileUploadService
from ...services.admin_service import AdminService
from ...models.admin_action import ActionType

router = APIRouter(prefix="/sections", tags=["Admin - Section Files"])


@router.post(
    "/{course_id}/{section_name}/files",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Upload PDF to section",
    description="Upload a PDF file to a specific course section",
)
async def upload_section_pdf(
    course_id: str,
    section_name: str,
    file: UploadFile = File(...),
    description: str = Form(""),
    current_user: User = Depends(admin_required),
):
    """
    Upload PDF file to a course section

    Args:
        course_id: Course ID
        section_name: Section name
        file: PDF file to upload
        description: Optional description for the file
    """
    try:
        # Validate course_id
        if not ObjectId.is_valid(course_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid course ID format",
            )

        # Get course
        course = await Course.get(course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
            )

        # Check if section exists
        section = course.get_section(section_name)
        if not section:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Section not found"
            )

        # Upload PDF file
        file_url = await FileUploadService.upload_section_pdf(
            file, course_id, section_name
        )

        # Create section file record
        section_file = SectionFile(
            filename=file.filename or "document.pdf",
            original_filename=file.filename or "document.pdf",
            file_url=file_url,
            file_size_kb=int(file.size / 1024) if file.size else 0,
            file_type="pdf",
            uploaded_by=str(current_user.id),
            description=description.strip() if description else None,
        )

        # Add file to section
        success = await course.add_file_to_section(section_name, section_file)
        if not success:
            # If adding to course failed, clean up uploaded file
            await FileUploadService.delete_section_pdf(file_url)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add file to section",
            )

        # Log admin action
        await AdminService.log_admin_action(
            str(current_user.id),
            ActionType.CREATE,
            "section_files",
            section_file.id,
            {
                "action": "pdf_uploaded",
                "course_id": course_id,
                "section_name": section_name,
                "filename": section_file.filename,
                "file_size_kb": section_file.file_size_kb,
            },
        )

        return AdminService.format_response(
            "PDF uploaded successfully",
            data={
                "id": section_file.id,
                "filename": section_file.filename,
                "original_filename": section_file.original_filename,
                "file_url": section_file.file_url,
                "file_size_kb": section_file.file_size_kb,
                "uploaded_at": section_file.uploaded_at.isoformat(),
                "is_active": section_file.is_active,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload PDF: {str(e)}",
        )


@router.get(
    "/{course_id}/{section_name}/files",
    response_model=Dict[str, Any],
    summary="Get section files",
    description="Get all files uploaded to a specific course section",
)
async def get_section_files(
    course_id: str,
    section_name: str,
    current_user: User = Depends(admin_required),
):
    """Get all files for a specific section"""
    try:
        # Validate course_id
        if not ObjectId.is_valid(course_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid course ID format",
            )

        # Get course
        course = await Course.get(course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
            )

        # Check if section exists
        section = course.get_section(section_name)
        if not section:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Section not found"
            )

        # Get section files
        files = course.get_section_files(section_name)

        # Format response
        file_data = [
            {
                "id": file.id,
                "filename": file.filename,
                "original_filename": file.original_filename,
                "file_url": file.file_url,
                "file_size_kb": file.file_size_kb,
                "file_type": file.file_type,
                "uploaded_at": file.uploaded_at.isoformat(),
                "uploaded_by": file.uploaded_by,
                "description": file.description,
                "is_active": file.is_active,
            }
            for file in files
        ]

        return AdminService.format_response(
            "Section files retrieved successfully",
            data={
                "course_id": course_id,
                "section_name": section_name,
                "files": file_data,
                "total_files": len(files),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve section files: {str(e)}",
        )


@router.delete(
    "/{course_id}/{section_name}/files/{file_id}",
    response_model=Dict[str, Any],
    summary="Delete section file",
    description="Delete a specific file from a course section",
)
async def delete_section_file(
    course_id: str,
    section_name: str,
    file_id: str,
    current_user: User = Depends(admin_required),
):
    """Delete a file from a specific section"""
    try:
        # Validate course_id
        if not ObjectId.is_valid(course_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid course ID format",
            )

        # Get course
        course = await Course.get(course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
            )

        # Check if section exists
        section = course.get_section(section_name)
        if not section:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Section not found"
            )

        # Get the file to delete
        file_to_delete = course.get_section_file(section_name, file_id)
        if not file_to_delete:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
            )

        # Delete file from storage
        delete_success = await FileUploadService.delete_section_pdf(
            file_to_delete.file_url
        )
        if not delete_success:
            print(
                f"Warning: Failed to delete file from storage: {file_to_delete.file_url}"
            )

        # Remove file from section
        success = await course.remove_file_from_section(section_name, file_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to remove file from section",
            )

        # Log admin action
        await AdminService.log_admin_action(
            str(current_user.id),
            ActionType.DELETE,
            "section_files",
            file_id,
            {
                "action": "pdf_deleted",
                "course_id": course_id,
                "section_name": section_name,
                "filename": file_to_delete.filename,
            },
        )

        return AdminService.format_response(
            "File deleted successfully",
            data={
                "file_id": file_id,
                "filename": file_to_delete.filename,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete file: {str(e)}",
        )
