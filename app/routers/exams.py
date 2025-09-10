from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from ..models.exam import Exam, ExamSubCategory
from ..models.admin_action import AdminAction, ActionType
from ..models.user import User
from ..models.enums import ExamCategory
from ..dependencies import admin_required, get_current_user


router = APIRouter(prefix="/api/v1/exams", tags=["Exams"])


class ExamCreateRequest(BaseModel):
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

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Complete JEE Main",
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
            }
        }


class ExamUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
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


class ExamResponse(BaseModel):
    id: str
    title: str
    code: str
    category: str
    sub_category: str
    description: str
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
