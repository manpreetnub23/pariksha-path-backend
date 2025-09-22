"""
File upload service for DigitalOcean Spaces
"""

import boto3
import uuid
import re
from typing import Optional, List
from fastapi import UploadFile, HTTPException, status
from PIL import Image
import io
import os
from datetime import datetime

from ..config import settings


class FileUploadService:
    """Service for handling file uploads to DigitalOcean Spaces"""

    # Allowed image types
    ALLOWED_IMAGE_TYPES = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
    }

    # Allowed PDF types
    ALLOWED_PDF_TYPES = {
        "application/pdf": ".pdf",
    }

    # Maximum file sizes
    MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB for images
    MAX_PDF_SIZE = 50 * 1024 * 1024  # 50MB for PDFs

    @staticmethod
    def _get_s3_client():
        """Get DigitalOcean Spaces S3 client"""
        return boto3.client(
            "s3",
            endpoint_url=settings.DO_SPACES_ENDPOINT,
            aws_access_key_id=settings.DO_SPACES_KEY,
            aws_secret_access_key=settings.DO_SPACES_SECRET,
            region_name=settings.DO_SPACES_REGION,
        )

    @staticmethod
    def _validate_image(file: UploadFile) -> None:
        """Validate uploaded image file"""
        # Check file type
        if file.content_type not in FileUploadService.ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Allowed types: {', '.join(FileUploadService.ALLOWED_IMAGE_TYPES.keys())}",
            )

        # Check file size
        if file.size and file.size > FileUploadService.MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Maximum size: {FileUploadService.MAX_IMAGE_SIZE // (1024*1024)}MB",
            )

    @staticmethod
    def _validate_pdf(file: UploadFile) -> None:
        """Validate uploaded PDF file"""
        # Check file type
        if file.content_type not in FileUploadService.ALLOWED_PDF_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Allowed types: {', '.join(FileUploadService.ALLOWED_PDF_TYPES.keys())}",
            )

        # Check file size
        if file.size and file.size > FileUploadService.MAX_PDF_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Maximum size: {FileUploadService.MAX_PDF_SIZE // (1024*1024)}MB",
            )

    @staticmethod
    def _optimize_image(file_content: bytes, max_width: int = 1200) -> bytes:
        """Optimize image for web delivery"""
        try:
            # Open image
            image = Image.open(io.BytesIO(file_content))

            # Convert to RGB if necessary
            if image.mode in ("RGBA", "LA", "P"):
                image = image.convert("RGB")

            # Resize if too large
            if image.width > max_width:
                ratio = max_width / image.width
                new_height = int(image.height * ratio)
                image = image.resize((max_width, new_height), Image.Resampling.LANCZOS)

            # Save as optimized JPEG
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=85, optimize=True)
            return output.getvalue()

        except Exception as e:
            # If optimization fails, return original content
            print(f"Image optimization failed: {str(e)}")
            return file_content

    @staticmethod
    def _generate_file_path(
        question_id: str,
        image_type: str,
        file_extension: str,
        option_index: Optional[int] = None,
    ) -> str:
        """Generate file path for uploaded image"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]

        if option_index is not None:
            return f"images/{question_id}_{image_type}_option_{option_index}_{timestamp}_{unique_id}{file_extension}"
        else:
            return f"images/{question_id}_{image_type}_{timestamp}_{unique_id}{file_extension}"

    @staticmethod
    def _generate_section_file_path(
        course_id: str,
        section_name: str,
        filename: str,
        file_extension: str,
    ) -> str:
        """Generate file path for uploaded section file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]

        # Clean filename for safe storage
        safe_filename = re.sub(r"[^a-zA-Z0-9._-]", "_", filename)
        safe_section = re.sub(r"[^a-zA-Z0-9._-]", "_", section_name)

        return f"courses/{course_id}/sections/{safe_section}/{safe_filename}_{timestamp}_{unique_id}{file_extension}"

    @staticmethod
    async def upload_question_image(
        file: UploadFile,
        question_id: str,
        image_type: str,
        option_index: Optional[int] = None,
    ) -> str:
        """
        Upload image for question, option, explanation, or remarks

        Args:
            file: Uploaded file
            question_id: Question ID
            image_type: Type of image ("question", "option", "explanation", "remarks")
            option_index: Index of option (only for option images)

        Returns:
            Public URL of uploaded image
        """
        try:
            # Validate image
            FileUploadService._validate_image(file)

            # Read file content
            file_content = await file.read()

            # Optimize image
            optimized_content = FileUploadService._optimize_image(file_content)

            # Generate file path
            file_extension = FileUploadService.ALLOWED_IMAGE_TYPES[file.content_type]
            file_path = FileUploadService._generate_file_path(
                question_id, image_type, file_extension, option_index
            )

            # Upload to DigitalOcean Spaces
            s3_client = FileUploadService._get_s3_client()
            s3_client.put_object(
                Bucket=settings.DO_SPACES_BUCKET,
                Key=file_path,
                Body=optimized_content,
                ContentType=file.content_type,
                ACL="public-read",
            )

            # Return public URL
            if settings.DO_SPACES_CDN_ENDPOINT:
                return f"{settings.DO_SPACES_CDN_ENDPOINT}/{file_path}"
            else:
                return f"{settings.DO_SPACES_ENDPOINT}/{settings.DO_SPACES_BUCKET}/{file_path}"

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload image: {str(e)}",
            )

    @staticmethod
    async def delete_question_image(image_url: str) -> bool:
        """
        Delete image from DigitalOcean Spaces

        Args:
            image_url: Public URL of image to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            # Extract file path from URL
            if (
                settings.DO_SPACES_CDN_ENDPOINT
                and settings.DO_SPACES_CDN_ENDPOINT in image_url
            ):
                file_path = image_url.replace(f"{settings.DO_SPACES_CDN_ENDPOINT}/", "")
            elif settings.DO_SPACES_ENDPOINT in image_url:
                file_path = image_url.replace(
                    f"{settings.DO_SPACES_ENDPOINT}/{settings.DO_SPACES_BUCKET}/", ""
                )
            else:
                return False

            # Delete from DigitalOcean Spaces
            s3_client = FileUploadService._get_s3_client()
            s3_client.delete_object(Bucket=settings.DO_SPACES_BUCKET, Key=file_path)

            return True

        except Exception as e:
            print(f"Failed to delete image {image_url}: {str(e)}")
            return False

    @staticmethod
    async def delete_multiple_images(image_urls: List[str]) -> int:
        """
        Delete multiple images from DigitalOcean Spaces

        Args:
            image_urls: List of public URLs to delete

        Returns:
            Number of successfully deleted images
        """
        deleted_count = 0
        for image_url in image_urls:
            if await FileUploadService.delete_question_image(image_url):
                deleted_count += 1

        return deleted_count

    @staticmethod
    async def upload_section_pdf(
        file: UploadFile,
        course_id: str,
        section_name: str,
    ) -> str:
        """
        Upload PDF file for a course section

        Args:
            file: Uploaded PDF file
            course_id: Course ID
            section_name: Section name

        Returns:
            Public URL of uploaded PDF
        """
        try:
            # Validate PDF
            FileUploadService._validate_pdf(file)

            # Read file content
            file_content = await file.read()

            # Generate file path
            file_extension = FileUploadService.ALLOWED_PDF_TYPES[file.content_type]
            file_path = FileUploadService._generate_section_file_path(
                course_id, section_name, file.filename or "document", file_extension
            )

            # Upload to DigitalOcean Spaces
            s3_client = FileUploadService._get_s3_client()
            s3_client.put_object(
                Bucket=settings.DO_SPACES_BUCKET,
                Key=file_path,
                Body=file_content,
                ContentType=file.content_type,
                ACL="public-read",
            )

            # Return public URL
            if settings.DO_SPACES_CDN_ENDPOINT:
                return f"{settings.DO_SPACES_CDN_ENDPOINT}/{file_path}"
            else:
                return f"{settings.DO_SPACES_ENDPOINT}/{settings.DO_SPACES_BUCKET}/{file_path}"

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload PDF: {str(e)}",
            )

    @staticmethod
    async def delete_section_pdf(pdf_url: str) -> bool:
        """
        Delete PDF file from DigitalOcean Spaces

        Args:
            pdf_url: Public URL of PDF to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            # Extract file path from URL
            if (
                settings.DO_SPACES_CDN_ENDPOINT
                and settings.DO_SPACES_CDN_ENDPOINT in pdf_url
            ):
                file_path = pdf_url.replace(f"{settings.DO_SPACES_CDN_ENDPOINT}/", "")
            elif settings.DO_SPACES_ENDPOINT in pdf_url:
                file_path = pdf_url.replace(
                    f"{settings.DO_SPACES_ENDPOINT}/{settings.DO_SPACES_BUCKET}/", ""
                )
            else:
                return False

            # Delete from DigitalOcean Spaces
            s3_client = FileUploadService._get_s3_client()
            s3_client.delete_object(Bucket=settings.DO_SPACES_BUCKET, Key=file_path)

            return True

        except Exception as e:
            print(f"Failed to delete PDF {pdf_url}: {str(e)}")
            return False
