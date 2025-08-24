from beanie import Document
from pydantic import Field
from typing import List, Optional
from datetime import datetime, timezone
from enum import Enum


class ResultType(str, Enum):
    TESTIMONIAL = "testimonial"
    TOPPER = "topper"
    SELECTION = "selection"


class Result(Document):
    student_name: str
    exam_name: str  # e.g., "NEET 2023", "JEE Advanced 2023"
    result_type: ResultType

    # Achievement details
    rank: Optional[int] = None
    marks: Optional[float] = None
    percentage: Optional[float] = None

    # Content
    testimonial_text: Optional[str] = None
    video_url: Optional[str] = None
    photo_url: str

    # Categorization
    exam_category: str  # Medical, Engineering, etc.
    year: int
    is_featured: bool = False

    # Verification
    is_verified: bool = True
    verification_document: Optional[str] = None

    # Admin
    added_by: str
    is_active: bool = True

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "results"

    def update_timestamp(self):
        self.updated_at = datetime.now(timezone.utc)
