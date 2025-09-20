"""
File upload endpoints for images and PDFs
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from typing import List, Optional
import aiofiles
import os
from datetime import datetime
from PIL import Image
import io

from ..dependencies import admin_required
from ..models.user import User
from ..services.storage import storage_service
from ..models.question import ImageAttachment

router = APIRouter(prefix="/api/v1/uploads", tags=["uploads"])


@router.post(
    "/images",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Upload images",
    description="Upload one or more images to DigitalOcean Spaces",
)
async def upload_images(
    files: List[UploadFile] = File(...), current_user: User = Depends(admin_required)
):
    """Upload multiple images"""
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No files provided"
        )

    # Validate file types
    allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    for file in files:
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File {file.filename} is not a supported image type",
            )

    uploaded_files = []
    errors = []

    for file in files:
        try:
            # Read file content
            content = await file.read()

            # Extract dimensions
            dimensions = None
            try:
                with Image.open(io.BytesIO(content)) as img:
                    dimensions = {"width": img.width, "height": img.height}
            except Exception as e:
                print(f"Could not extract dimensions for {file.filename}: {e}")
                # Continue without dimensions if extraction fails

            # Upload to DigitalOcean Spaces
            public_url, metadata = await storage_service.upload_image(
                content, file.filename
            )

            # Create ImageAttachment object
            image_attachment = ImageAttachment(
                url=public_url,
                alt_text=file.filename,
                caption="",
                order=len(uploaded_files),
                file_size=metadata["file_size"],
                dimensions=dimensions,
            )

            uploaded_files.append(
                {
                    "filename": file.filename,
                    "url": public_url,
                    "metadata": {**metadata, "dimensions": dimensions},
                    "image_attachment": image_attachment.dict(),
                }
            )

        except Exception as e:
            errors.append({"filename": file.filename, "error": str(e)})

    return {
        "message": f"Successfully uploaded {len(uploaded_files)} images",
        "uploaded_files": uploaded_files,
        "errors": errors,
        "total_uploaded": len(uploaded_files),
        "total_errors": len(errors),
    }


@router.post(
    "/images/single",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Upload single image",
    description="Upload a single image to DigitalOcean Spaces",
)
async def upload_single_image(
    file: UploadFile = File(...), current_user: User = Depends(admin_required)
):
    """Upload a single image"""
    # Validate file type
    allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is not a supported image type",
        )

    try:
        # Read file content
        content = await file.read()

        # Extract dimensions
        dimensions = None
        try:
            with Image.open(io.BytesIO(content)) as img:
                dimensions = {"width": img.width, "height": img.height}
        except Exception as e:
            print(f"Could not extract dimensions for {file.filename}: {e}")
            # Continue without dimensions if extraction fails

        # Upload to DigitalOcean Spaces
        public_url, metadata = await storage_service.upload_image(
            content, file.filename
        )

        # Create ImageAttachment object
        image_attachment = ImageAttachment(
            url=public_url,
            alt_text=file.filename,
            caption="",
            order=0,
            file_size=metadata["file_size"],
            dimensions=dimensions,
        )

        return {
            "message": "Image uploaded successfully",
            "filename": file.filename,
            "url": public_url,
            "metadata": {**metadata, "dimensions": dimensions},
            "image_attachment": image_attachment.dict(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload image: {str(e)}",
        )


@router.post(
    "/pdfs",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Upload PDFs",
    description="Upload one or more PDF files to DigitalOcean Spaces",
)
async def upload_pdfs(
    files: List[UploadFile] = File(...), current_user: User = Depends(admin_required)
):
    """Upload multiple PDF files"""
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No files provided"
        )

    # Validate file types
    for file in files:
        if file.content_type != "application/pdf":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File {file.filename} is not a PDF",
            )

    uploaded_files = []
    errors = []

    for file in files:
        try:
            # Read file content
            content = await file.read()

            # Upload to DigitalOcean Spaces
            public_url, metadata = await storage_service.upload_pdf(
                content, file.filename
            )

            uploaded_files.append(
                {"filename": file.filename, "url": public_url, "metadata": metadata}
            )

        except Exception as e:
            errors.append({"filename": file.filename, "error": str(e)})

    return {
        "message": f"Successfully uploaded {len(uploaded_files)} PDFs",
        "uploaded_files": uploaded_files,
        "errors": errors,
        "total_uploaded": len(uploaded_files),
        "total_errors": len(errors),
    }


@router.delete(
    "/files/{file_path:path}",
    response_model=dict,
    summary="Delete file",
    description="Delete a file from DigitalOcean Spaces",
)
async def delete_file(file_path: str, current_user: User = Depends(admin_required)):
    """Delete a file from storage"""
    try:
        success = await storage_service.delete_file(file_path)

        if success:
            return {"message": "File deleted successfully", "file_path": file_path}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found or could not be deleted",
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete file: {str(e)}",
        )


@router.get(
    "/files/{file_path:path}/info",
    response_model=dict,
    summary="Get file info",
    description="Get information about a file in storage",
)
async def get_file_info(file_path: str, current_user: User = Depends(admin_required)):
    """Get file information"""
    try:
        file_info = await storage_service.get_file_info(file_path)

        if file_info:
            return {"file_path": file_path, "info": file_info}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get file info: {str(e)}",
        )
        
        
        
@router.get(
    "/courses/{slug}/sections/{section}/materials",
    response_model=dict,
)
async def list_section_materials(slug: str, section: str, current_user: User = Depends(admin_required)):
    try:
        # folder_path = f"pdfs/{slug}/{section}/"  # future me use karenge
        folder_path = "pariksha-path-bucket/pdfs/2025/09/19/"    
        files = await storage_service.list_files(prefix=folder_path)
        print("DEBUG prefix used in router:", folder_path)
        return {"materials": files}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list materials: {str(e)}"
        )

@router.get("/debug-keys")
async def debug_keys():
    try:
        resp = storage_service.s3_client.list_objects_v2(
            Bucket=storage_service.bucket_name,
            Prefix=""   # saare objects dikhayega
        )
        return resp
    except Exception as e:
        return {
            "error": str(e),
            "type": str(type(e))
        }
