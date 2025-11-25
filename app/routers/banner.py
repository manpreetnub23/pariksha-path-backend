from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from typing import Dict, Any

from ..dependencies import get_current_user
from ..models.user import User
from ..services.file_upload_service import FileUploadService
from ..services.banner_service import BannerService

router = APIRouter(prefix="/api/v1/banner", tags=["Banner"])


@router.post("/upload", response_model=Dict[str, Any])
async def upload_banner(
    file: UploadFile = File(...),
    title: str = "Banner",
    current_user: User = Depends(get_current_user),
):
    try:
        # ✅ 1. Upload to DigitalOcean
        url = await FileUploadService.upload_banner_image(file, title)
        
        print("iska jo url hai woh url hai :",url)

        print("file upload ho gayi hai mittar")
        # ✅ 2. Save to Mongo
        banner = await BannerService.create_banner(
            image_url=url,
            title=title
        )
        print("mongo mein save ho gayi hai mittar")

        return {
            "success": True,
            "message": "Banner uploaded & saved to DB",
            "banner": {
                "id": str(banner.id),
                "title": banner.title,
                "image_url": banner.image_url,
                "is_active": banner.is_active,
                "position": banner.position
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=Dict[str, Any])
async def get_all_banners():
    banners = await BannerService.get_all_banners()

    return {
        "success": True,
        "count": len(banners),
        "banners": [
            {
                "id": str(b.id),
                "title": b.title,
                "image_url": b.image_url,
                "position": b.position,
                "is_active": b.is_active,
                "created_at": b.created_at,
            }
            for b in banners
        ]
    }

@router.delete("/{banner_id}", response_model=Dict[str, Any])
async def delete_banner(
    banner_id: str,
    current_user: User = Depends(get_current_user),
):
    try:
        banner = await BannerService.get_banner_by_id(banner_id)

        if not banner:
            raise HTTPException(404, "Banner not found")

        # delete image from DO
        if banner.image_url:
            await FileUploadService.delete_question_image(banner.image_url)

        # delete from DB
        await BannerService.delete_banner(banner_id)

        return {"success": True, "message": "Banner deleted successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
