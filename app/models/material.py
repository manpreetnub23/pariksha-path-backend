from beanie import Document
from pydantic import Field
from typing import List, Optional
from datetime import datetime, timezone
from enum import Enum


class MaterialType(str, Enum):
    PDF = "pdf"
    DOC = "doc"
    VIDEO = "video"
    LINK = "link"
    PYQ = "pyq"  # Previous Year Questions


class MaterialAccessType(str, Enum):
    FREE = "free"  # Available to all users
    PREMIUM = "premium"  # Requires payment/subscription
    ENROLLED = "enrolled"  # Available to enrolled students only


class Material(Document):
    title: str
    description: str
    material_type: MaterialType

    # Content
    file_url: Optional[str] = None
    external_link: Optional[str] = None

    # Organization
    course_id: Optional[str] = None  # Associated course
    exam_category: str  # Medical, Engineering, etc.
    subject: Optional[str] = None
    topic: Optional[str] = None

    # Access control
    access_type: MaterialAccessType = MaterialAccessType.PREMIUM
    is_public: bool = True
    price: Optional[float] = None  # If individually purchasable

    # Admin
    created_by: str
    is_active: bool = True

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "materials"

    def update_timestamp(self):
        self.updated_at = datetime.now(timezone.utc)
