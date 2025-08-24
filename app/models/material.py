from pydantic import Field
from typing import List, Optional
from datetime import datetime
from .enums import MaterialType, MaterialAccessType
from .base import BaseDocument


class Material(BaseDocument):
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

    class Settings:
        name = "materials"
