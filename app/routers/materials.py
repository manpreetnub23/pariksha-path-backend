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
    BackgroundTasks,
)
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl
from uuid import UUID

from ..models.study_material import StudyMaterial, UserMaterialProgress
from ..models.admin_action import AdminAction, ActionType
from ..models.user import User
from ..models.enums import (
    ExamCategory,
    MaterialType,
    MaterialAccessType,
    MaterialCategory,
)
from ..dependencies import admin_required, get_current_user
from ..utils import paginate_query, get_or_404

router = APIRouter(prefix="/api/v1/materials", tags=["Study Materials"])


# Request/Response Models
class StudyMaterialCreate(BaseModel):
    title: str
    description: str
    format: MaterialType
    category: MaterialCategory
    file_url: HttpUrl
    file_size_kb: int = 0
    preview_url: Optional[HttpUrl] = None
    access_type: MaterialAccessType = MaterialAccessType.PREMIUM
    exam_category: str
    exam_subcategory: Optional[str] = None
    subject: str
    topic: Optional[str] = None
    tags: List[str] = []
    course_ids: List[str] = []
    is_free: bool = False

    class Config:
        json_schema_extra = {
            "example": {
                "title": "JEE Main Physics Formula Sheet",
                "description": "Comprehensive formula sheet for JEE Main Physics preparation",
                "format": "pdf",
                "category": "formula_sheet",
                "file_url": "https://storage.example.com/files/jee-physics-formulas.pdf",
                "file_size_kb": 1024,
                "access_type": "premium",
                "exam_category": "engineering",
                "exam_subcategory": "JEE Main",
                "subject": "Physics",
                "topic": "Mechanics",
                "tags": ["formulas", "physics", "jee"],
                "course_ids": [],
                "is_free": False,
            }
        }


class StudyMaterialUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    format: Optional[MaterialType] = None
    category: Optional[MaterialCategory] = None
    file_url: Optional[HttpUrl] = None
    file_size_kb: Optional[int] = None
    preview_url: Optional[HttpUrl] = None
    access_type: Optional[MaterialAccessType] = None
    exam_category: Optional[str] = None
    exam_subcategory: Optional[str] = None
    subject: Optional[str] = None
    topic: Optional[str] = None
    tags: Optional[List[str]] = None
    course_ids: Optional[List[str]] = None
    is_active: Optional[bool] = None


class MaterialProgressUpdate(BaseModel):
    completion_percentage: float = Field(..., ge=0, le=100)
    user_rating: Optional[int] = Field(None, ge=1, le=5)
    user_notes: Optional[str] = None
    bookmarked: Optional[bool] = None


# List materials with filtering
@router.get("/")
async def list_materials(
    category: Optional[MaterialCategory] = Query(
        None, description="Filter by material category"
    ),
    format: Optional[MaterialType] = Query(
        None, description="Filter by material format"
    ),
    exam_category: Optional[ExamCategory] = Query(
        None, description="Filter by exam category"
    ),
    exam_subcategory: Optional[str] = Query(
        None, description="Filter by exam subcategory"
    ),
    subject: Optional[str] = Query(None, description="Filter by subject"),
    topic: Optional[str] = Query(None, description="Filter by topic"),
    search: Optional[str] = Query(None, description="Search in title and description"),
    is_free: Optional[bool] = Query(None, description="Filter by free/paid status"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort order (asc or desc)"),
    page: int = Query(1, description="Page number", ge=1),
    limit: int = Query(10, description="Items per page", ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    """Get all available study materials with filtering and pagination"""
    try:
        # Build query filters
        query_filters = {"is_active": True}

        # Add filters if provided
        if category:
            query_filters["category"] = category

        if format:
            query_filters["format"] = format

        if exam_category:
            query_filters["exam_category"] = exam_category.value

        if exam_subcategory:
            query_filters["exam_subcategory"] = exam_subcategory

        if subject:
            query_filters["subject"] = subject

        if topic:
            query_filters["topic"] = topic

        if is_free is not None:
            query_filters["is_free"] = is_free

        if search:
            query_filters["$or"] = [
                {"title": {"$regex": search, "$options": "i"}},
                {"description": {"$regex": search, "$options": "i"}},
            ]

        # Access control - non-admin users can only see materials they have access to
        if current_user.role != "admin":
            # Free materials or premium if user has premium access
            access_conditions = [
                {"access_type": MaterialAccessType.FREE},
            ]

            # Add premium access condition if user has it
            if current_user.has_premium_access:
                access_conditions.append({"access_type": MaterialAccessType.PREMIUM})

            # Add enrolled courses condition
            if current_user.enrolled_courses:
                access_conditions.append(
                    {
                        "access_type": MaterialAccessType.ENROLLED,
                        "course_ids": {"$in": current_user.enrolled_courses},
                    }
                )
                access_conditions.append(
                    {
                        "access_type": MaterialAccessType.COURSE_ONLY,
                        "course_ids": {"$in": current_user.enrolled_courses},
                    }
                )

            # Add access filter to query
            query_filters["$or"] = access_conditions

        # Transform function to add user-specific data
        async def transform_material(material):
            result = {
                "id": str(material.id),
                "title": material.title,
                "description": material.description,
                "format": material.format,
                "category": material.category,
                "exam_category": material.exam_category,
                "exam_subcategory": material.exam_subcategory,
                "subject": material.subject,
                "topic": material.topic,
                "tags": material.tags,
                "download_count": material.download_count,
                "created_at": material.created_at,
            }

            # Add user progress data if available
            progress = await UserMaterialProgress.find_one(
                {"user_id": str(current_user.id), "material_id": str(material.id)}
            )

            if progress:
                result["user_progress"] = {
                    "completion_percentage": progress.completion_percentage,
                    "bookmarked": progress.bookmarked,
                    "user_rating": progress.user_rating,
                    "last_accessed": progress.last_accessed,
                }

            return result

        # Use pagination utility
        materials, pagination = await paginate_query(
            StudyMaterial,
            query_filters,
            sort_by,
            sort_order,
            page,
            limit,
            transform_material,
        )

        return {
            "message": "Study materials retrieved successfully",
            "data": materials,
            "pagination": pagination,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve study materials: {str(e)}",
        )


# Get specific material details
@router.get("/{material_id}")
async def get_material(
    material_id: str, current_user: User = Depends(get_current_user)
):
    """Get detailed information about a specific study material"""
    try:
        # Get material
        material = await get_or_404(
            StudyMaterial, material_id, detail="Study material not found"
        )

        # Check if material is active
        if not material.is_active:
            # Admin can see inactive materials
            if current_user.role != "admin":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Study material not found",
                )

        # Check access permissions for non-admins
        if current_user.role != "admin":
            has_access = False

            # Check access type
            if material.access_type == MaterialAccessType.FREE:
                has_access = True
            elif (
                material.access_type == MaterialAccessType.PREMIUM
                and current_user.has_premium_access
            ):
                has_access = True
            elif material.access_type in [
                MaterialAccessType.ENROLLED,
                MaterialAccessType.COURSE_ONLY,
            ]:
                # Check if user is enrolled in any of the material's courses
                for course_id in material.course_ids:
                    if course_id in current_user.enrolled_courses:
                        has_access = True
                        break

            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have access to this material",
                )

        # Update view count
        material.view_count += 1
        await material.save()

        # Check if user progress record exists, create if not
        progress = await UserMaterialProgress.find_one(
            {"user_id": str(current_user.id), "material_id": material_id}
        )

        if not progress:
            progress = UserMaterialProgress(
                user_id=str(current_user.id), material_id=material_id
            )
            await progress.insert()
        else:
            # Update access
            progress.update_access()
            await progress.save()

        # Format response
        response = {
            "id": str(material.id),
            "title": material.title,
            "description": material.description,
            "format": material.format,
            "category": material.category,
            "file_url": material.file_url,
            "file_size_kb": material.file_size_kb,
            "preview_url": material.preview_url,
            "exam_category": material.exam_category,
            "exam_subcategory": material.exam_subcategory,
            "subject": material.subject,
            "topic": material.topic,
            "tags": material.tags,
            "download_count": material.download_count,
            "view_count": material.view_count,
            "rating": material.rating,
            "review_count": material.review_count,
            "created_at": material.created_at,
            "updated_at": material.updated_at,
            "user_progress": {
                "completion_percentage": progress.completion_percentage,
                "view_count": progress.view_count,
                "download_count": progress.download_count,
                "user_rating": progress.user_rating,
                "bookmarked": progress.bookmarked,
                "user_notes": progress.user_notes,
                "first_accessed": progress.first_accessed,
                "last_accessed": progress.last_accessed,
            },
        }

        # Add course information if admin
        if current_user.role == "admin":
            response["course_ids"] = material.course_ids
            response["is_active"] = material.is_active
            response["access_type"] = material.access_type
            response["created_by"] = material.created_by
            response["version"] = material.version

        return {
            "message": "Study material retrieved successfully",
            "material": response,
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve study material: {str(e)}",
        )


# Download material
@router.get("/{material_id}/download")
async def download_material(
    material_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    """Get download URL for a study material and track download"""
    try:
        # Get material
        material = await get_or_404(
            StudyMaterial, material_id, detail="Study material not found"
        )

        # Check if material is active
        if not material.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Study material not found"
            )

        # Check access permissions for non-admins
        if current_user.role != "admin":
            has_access = False

            # Check access type
            if material.access_type == MaterialAccessType.FREE:
                has_access = True
            elif (
                material.access_type == MaterialAccessType.PREMIUM
                and current_user.has_premium_access
            ):
                has_access = True
            elif material.access_type in [
                MaterialAccessType.ENROLLED,
                MaterialAccessType.COURSE_ONLY,
            ]:
                # Check if user is enrolled in any of the material's courses
                for course_id in material.course_ids:
                    if course_id in current_user.enrolled_courses:
                        has_access = True
                        break

            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have access to this material",
                )

        # Track download in background
        async def track_download():
            # Update material download count
            await material.track_download(str(current_user.id))

            # Update user progress
            progress = await UserMaterialProgress.find_one(
                {"user_id": str(current_user.id), "material_id": material_id}
            )

            if progress:
                progress.download_count += 1
                progress.last_accessed = datetime.now(timezone.utc)
                await progress.save()

        background_tasks.add_task(track_download)

        # Return download URL
        return {
            "message": "Download URL generated successfully",
            "download_url": material.file_url,
            "filename": material.title,
            "file_size_kb": material.file_size_kb,
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download material: {str(e)}",
        )


# Update user progress
@router.put("/{material_id}/progress")
async def update_material_progress(
    material_id: str,
    progress_data: MaterialProgressUpdate,
    current_user: User = Depends(get_current_user),
):
    """Update user's progress for a study material"""
    try:
        # Check if material exists
        material = await get_or_404(
            StudyMaterial, material_id, detail="Study material not found"
        )

        # Get or create user progress
        progress = await UserMaterialProgress.find_one(
            {"user_id": str(current_user.id), "material_id": material_id}
        )

        if not progress:
            progress = UserMaterialProgress(
                user_id=str(current_user.id), material_id=material_id
            )

        # Update fields
        progress.completion_percentage = progress_data.completion_percentage

        if progress_data.completion_percentage >= 100:
            progress.completed = True

        if progress_data.user_rating is not None:
            # If user is changing their rating, update material's overall rating
            old_rating = progress.user_rating
            progress.user_rating = progress_data.user_rating

            # Update material rating
            if old_rating is None:
                # New rating
                material.review_count += 1
                new_total = (
                    material.rating * (material.review_count - 1)
                    + progress_data.user_rating
                )
                material.rating = new_total / material.review_count
            else:
                # Changed rating
                new_total = (
                    material.rating * material.review_count
                    - old_rating
                    + progress_data.user_rating
                )
                material.rating = new_total / material.review_count

            await material.save()

        if progress_data.user_notes is not None:
            progress.user_notes = progress_data.user_notes

        if progress_data.bookmarked is not None:
            progress.bookmarked = progress_data.bookmarked

        # Save progress
        progress.last_accessed = datetime.now(timezone.utc)
        await progress.save()

        return {
            "message": "Progress updated successfully",
            "progress": {
                "completion_percentage": progress.completion_percentage,
                "completed": progress.completed,
                "user_rating": progress.user_rating,
                "bookmarked": progress.bookmarked,
            },
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update progress: {str(e)}",
        )


# Admin Routes


# Create new material (admin only)
@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_material(
    material_data: StudyMaterialCreate, current_user: User = Depends(admin_required)
):
    """Create a new study material (Admin only)"""
    try:
        # Create material
        new_material = StudyMaterial(
            title=material_data.title,
            description=material_data.description,
            format=material_data.format,
            category=material_data.category,
            file_url=str(material_data.file_url),
            file_size_kb=material_data.file_size_kb,
            preview_url=(
                str(material_data.preview_url) if material_data.preview_url else None
            ),
            access_type=material_data.access_type,
            exam_category=material_data.exam_category,
            exam_subcategory=material_data.exam_subcategory,
            subject=material_data.subject,
            topic=material_data.topic,
            tags=material_data.tags,
            course_ids=material_data.course_ids,
            created_by=str(current_user.id),
        )

        await new_material.insert()

        # Log admin action
        admin_action = AdminAction(
            admin_id=str(current_user.id),
            action_type=ActionType.CREATE,
            target_collection="study_materials",
            target_id=str(new_material.id),
            changes={"action": "material_created"},
        )
        await admin_action.insert()

        return {
            "message": "Study material created successfully",
            "material_id": str(new_material.id),
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create study material: {str(e)}",
        )


# Update material (admin only)
@router.put("/{material_id}")
async def update_material(
    material_id: str,
    material_data: StudyMaterialUpdate,
    current_user: User = Depends(admin_required),
):
    """Update an existing study material (Admin only)"""
    try:
        # Get material
        material = await get_or_404(
            StudyMaterial, material_id, detail="Study material not found"
        )

        # Track changes for audit log
        changes = {}

        # Update fields if provided
        update_dict = material_data.dict(exclude_unset=True)

        for field, value in update_dict.items():
            if value is not None:
                setattr(material, field, value)
                changes[field] = (
                    str(value) if not isinstance(value, list) else "updated"
                )

        # Increment version
        material.version += 1
        changes["version"] = material.version

        # Only update if there are changes
        if changes:
            material.update_timestamp()
            await material.save()

            # Log admin action
            admin_action = AdminAction(
                admin_id=str(current_user.id),
                action_type=ActionType.UPDATE,
                target_collection="study_materials",
                target_id=material_id,
                changes=changes,
            )
            await admin_action.insert()

            return {
                "message": "Study material updated successfully",
                "material_id": material_id,
                "changes": changes,
            }
        else:
            return {"message": "No changes to apply", "material_id": material_id}

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update study material: {str(e)}",
        )


# Delete material (admin only - soft delete)
@router.delete("/{material_id}")
async def delete_material(
    material_id: str, current_user: User = Depends(admin_required)
):
    """Delete (deactivate) a study material (Admin only)"""
    try:
        # Get material
        material = await get_or_404(
            StudyMaterial, material_id, detail="Study material not found"
        )

        # Check if material is already inactive
        if not material.is_active:
            return {
                "message": "Study material is already deactivated",
                "material_id": material_id,
            }

        # Soft delete by setting is_active=False
        material.is_active = False
        material.update_timestamp()
        await material.save()

        # Log admin action
        admin_action = AdminAction(
            admin_id=str(current_user.id),
            action_type=ActionType.DELETE,
            target_collection="study_materials",
            target_id=material_id,
            changes={"is_active": False},
        )
        await admin_action.insert()

        return {
            "message": "Study material deactivated successfully",
            "material_id": material_id,
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete study material: {str(e)}",
        )
