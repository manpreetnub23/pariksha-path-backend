from beanie import Document
from pydantic import Field
from typing import List, Optional
from datetime import datetime, timezone
from enum import Enum


class TestimonialType(str, Enum):
    TEXT = "text"
    VIDEO = "video"
    BOTH = "both"


class AchievementCategory(str, Enum):
    TOPPER = "topper"  # Overall top ranks
    SELECTION = "selection"  # Got selected in competitive exam
    IMPROVEMENT = "improvement"  # Significant score improvement


class Testimonial(Document):
    # Student details
    student_name: str
    photo_url: str
    user_id: Optional[str] = None  # If the student is a registered user

    # Achievement details
    exam_name: str  # e.g., "NEET 2023", "JEE Advanced 2023"
    exam_category: str  # Medical, Engineering, etc.
    achievement_category: AchievementCategory
    rank: Optional[int] = None
    marks: Optional[float] = None
    percentage: Optional[float] = None
    year: int

    # Content
    testimonial_type: TestimonialType
    text_content: Optional[str] = None
    video_url: Optional[str] = None

    # Display properties
    is_featured: bool = False
    display_order: int = 0  # For custom ordering on frontend
    tags: List[str] = []  # For filtering purposes

    # Verification
    is_verified: bool = True
    verification_document_url: Optional[str] = None

    # Admin
    added_by: str  # Admin user ID
    is_active: bool = True

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "testimonials"

    def update_timestamp(self):
        self.updated_at = datetime.now(timezone.utc)


class GalleryImage(Document):
    """Model for managing student achievement images in gallery"""

    title: str
    image_url: str
    student_name: str
    exam_name: str
    exam_category: str
    year: int
    achievement_text: str  # Brief description of achievement

    # Display properties
    is_featured: bool = False
    display_order: int = 0

    # Admin
    added_by: str
    is_active: bool = True

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "gallery_images"

    def update_timestamp(self):
        self.updated_at = datetime.now(timezone.utc)
