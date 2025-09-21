"""
Course-related Pydantic schemas for request/response models
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from ...models.enums import ExamCategory


class CourseCreateRequest(BaseModel):
    """Schema for creating a new course"""

    title: str
    code: str
    category: ExamCategory
    sub_category: str
    description: str
    price: float
    is_free: bool = False
    discount_percent: Optional[float] = None
    material_ids: List[str] = []
    test_series_ids: List[str] = []
    thumbnail_url: str
    icon_url: Optional[str] = None
    priority_order: int = 0
    banner_url: Optional[str] = None
    tagline: Optional[str] = None
    sections: List[str] = []

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Complete JEE Main Physics",
                "code": "JEE-PHY-001",
                "category": "engineering",
                "sub_category": "JEE Main",
                "description": "Comprehensive course for JEE Main Physics preparation",
                "price": 4999.0,
                "is_free": False,
                "discount_percent": 10.0,
                "material_ids": [],
                "test_series_ids": [],
                "thumbnail_url": "https://example.com/images/jee-physics.jpg",
                "icon_url": "https://example.com/icons/physics.png",
                "priority_order": 1,
                "banner_url": "https://example.com/banners/jee-physics-banner.jpg",
                "tagline": "Master Physics concepts for JEE Main",
                "sections": ["Physics", "Chemistry", "Biology"],
            }
        }


class CourseUpdateRequest(BaseModel):
    """Schema for updating a course"""

    title: Optional[str] = None
    description: Optional[str] = None
    sections: Optional[List[str]] = None
    price: Optional[float] = None
    is_free: Optional[bool] = None
    discount_percent: Optional[float] = None
    material_ids: Optional[List[str]] = None
    test_series_ids: Optional[List[str]] = None
    thumbnail_url: Optional[str] = None
    icon_url: Optional[str] = None
    priority_order: Optional[int] = None
    banner_url: Optional[str] = None
    tagline: Optional[str] = None
    is_active: Optional[bool] = None


class CourseResponse(BaseModel):
    """Schema for course response"""

    id: str
    title: str
    code: str
    category: str
    sub_category: str
    description: str
    sections: Optional[List[str]] = None
    price: float
    is_free: bool
    discount_percent: Optional[float] = None
    material_ids: List[str]
    test_series_ids: List[str]
    enrolled_students_count: int
    thumbnail_url: str
    icon_url: Optional[str] = None
    banner_url: Optional[str] = None
    tagline: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SectionCreateRequest(BaseModel):
    """Schema for creating a new section"""

    section_name: str


class SectionUpdateRequest(BaseModel):
    """Schema for updating a section"""

    new_section_name: str


class MockSubmitAnswer(BaseModel):
    """Schema for mock test answer submission"""

    question_id: str
    selected_option_order: Optional[int] = None
    selected_option_text: Optional[str] = None


class MockSubmitRequest(BaseModel):
    """Schema for mock test submission"""

    answers: List[MockSubmitAnswer]
    time_spent_seconds: Optional[int] = 0
    marked_for_review: Optional[List[str]] = []


class QuestionCountUpdateRequest(BaseModel):
    """Schema for updating section question count"""

    new_count: int = Field(..., embed=True)
