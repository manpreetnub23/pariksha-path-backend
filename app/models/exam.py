from beanie import Document
from pydantic import Field, BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from .enums import ExamCategory


class ExamSubCategory(BaseModel):
    """Specific exam within a category"""

    name: str  # e.g., "NEET", "JEE Main"
    description: Optional[str] = None
    icon_url: Optional[str] = None


class Exam(Document):
    # Basic info
    title: str
    code: str  # Unique exam code
    category: ExamCategory
    sub_category: str  # Specific exam (e.g., "NEET", "JEE Main")

    # Content details
    description: str
    syllabus_id: Optional[str] = None  # Reference to detailed syllabus model

    # Pricing
    price: float
    is_free: bool = False
    discount_percent: Optional[float] = None

    # Resources
    material_ids: List[str] = []  # References to study materials
    test_series_ids: List[str] = []  # References to associated test series

    # Display info
    icon_url: Optional[str] = None
    priority_order: int = 0  # For display ordering on frontend
    banner_url: Optional[str] = None  # Hero banner image
    tagline: Optional[str] = None  # Exam tagline for marketing

    # Stats
    enrolled_students_count: int = 0

    # Status
    is_active: bool = True
    created_by: str  # Admin ID

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "exams"

    def update_timestamp(self):
        self.updated_at = datetime.now(timezone.utc)
