from beanie import Document
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone
import uuid


class ExamInfoSection(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    header: str
    content: str
    order: int = 0
    is_active: bool = True


class ExamContent(Document):
    exam_code: str = Field(..., description="Unique slug like 'ssc-cgl', 'neet', 'jee-main'")
    title: str = Field(..., description="Exam name")
    description: Optional[str] = None

    exam_info_sections: List[ExamInfoSection] = Field(default_factory=list)

    banner_url: Optional[str] = None
    is_active: bool = True

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "exam_contents"

    def update_timestamp(self):
        self.updated_at = datetime.now(timezone.utc)
