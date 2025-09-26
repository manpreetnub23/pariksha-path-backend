from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from beanie import PydanticObjectId
from typing import List, Optional
from datetime import datetime, timezone
from ..models.exam_content import ExamContent, ExamInfoSection
from ..dependencies import admin_required, ensure_db  # admin auth dependency
from pydantic import BaseModel


router = APIRouter(prefix="/api/v1/exam-contents", tags=["Exam Contents"])


# ------------------------------
# Request models for Create/Update
# ------------------------------
class ExamInfoSectionIn(BaseModel):
    id: Optional[str] = None
    header: str
    content: str
    order: int = 0
    is_active: bool = True


class ExamContentIn(BaseModel):
    exam_code: str
    title: str
    description: Optional[str] = None
    linked_course_id: Optional[str] = None
    thumbnail_url: Optional[str] = None
    banner_url: Optional[str] = None
    exam_info_sections: List[ExamInfoSectionIn] = []


# ------------------------------
# Create new ExamContent
# ------------------------------
@router.post("/", response_model=ExamContent)
async def create_exam_content(
    data: ExamContentIn, admin=Depends(admin_required), db=Depends(ensure_db)
):
    print(f"🔄 POST /exam-contents/ called with exam_code: {data.exam_code}")

    # check if exam_code already exists
    existing = await ExamContent.find_one(ExamContent.exam_code == data.exam_code)

    if existing:
        print(f"❌ POST failed: ExamContent with exam_code '{data.exam_code}' already exists")
        raise HTTPException(
            status_code=400,
            detail=f"ExamContent with exam_code '{data.exam_code}' already exists. Use PUT to update existing content."
        )

    sections = [ExamInfoSection(**sec.dict()) for sec in data.exam_info_sections]

    new_exam_content = ExamContent(
        exam_code=data.exam_code,
        title=data.title,
        description=data.description,
        linked_course_id=data.linked_course_id,
        thumbnail_url=data.thumbnail_url,
        banner_url=data.banner_url,
        exam_info_sections=sections,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    await new_exam_content.insert()
    print(f"✅ POST successful: Created ExamContent with exam_code '{data.exam_code}'")
    return new_exam_content


# ------------------------------
# Get all ExamContents
# ------------------------------
@router.get("/", response_model=List[ExamContent])
async def get_all_exam_contents(admin=Depends(admin_required), db=Depends(ensure_db)):
    contents = await ExamContent.find().to_list()
    return contents


# ------------------------------
# Get ExamContent by exam_code
# ------------------------------
@router.get("/{exam_code}", response_model=ExamContent)
async def get_exam_content_by_code(exam_code: str, db=Depends(ensure_db)):
    content = await ExamContent.find_one(ExamContent.exam_code == exam_code)
    if not content:
        raise HTTPException(status_code=404, detail="ExamContent not found")
    return content


# ------------------------------
# Update ExamContent
# ------------------------------
@router.put("/{exam_code}", response_model=ExamContent)
async def update_exam_content(
    exam_code: str,
    data: ExamContentIn,
    admin=Depends(admin_required),
    db=Depends(ensure_db),
):
    print(f"🔄 PUT /exam-contents/{exam_code} called")

    content = await ExamContent.find_one(ExamContent.exam_code == exam_code)
    if not content:
        print(f"❌ PUT failed: ExamContent with exam_code '{exam_code}' not found")
        raise HTTPException(
            status_code=404,
            detail=f"ExamContent with exam_code '{exam_code}' not found. Use POST to create new content."
        )

    print(f"✅ PUT found existing content, updating exam_code '{exam_code}'")

    content.title = data.title
    content.description = data.description
    content.linked_course_id = data.linked_course_id
    content.thumbnail_url = data.thumbnail_url
    content.banner_url = data.banner_url
    content.exam_info_sections = [ExamInfoSection(**sec.dict()) for sec in data.exam_info_sections]
    content.updated_at = datetime.now(timezone.utc)

    await content.save()
    print(f"✅ PUT successful: Updated ExamContent with exam_code '{exam_code}'")
    return content


# ------------------------------
# Delete ExamContent
# ------------------------------
@router.delete("/{exam_code}")
async def delete_exam_content(exam_code: str, admin=Depends(admin_required), db=Depends(ensure_db)):
    content = await ExamContent.find_one(ExamContent.exam_code == exam_code)
    if not content:
        raise HTTPException(status_code=404, detail="ExamContent not found")
    await content.delete()
    return JSONResponse({"detail": "Deleted successfully"})
