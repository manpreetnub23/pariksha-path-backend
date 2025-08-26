from beanie import Document
from pydantic import EmailStr, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from .enums import UserRole, ExamCategory


class User(Document):
    name: str
    email: EmailStr
    phone: str
    password_hash: str
    role: UserRole = UserRole.STUDENT

    # Profile fields
    is_active: bool = True
    is_verified: bool = False
    is_email_verified: bool = False
    email_verification_otp: Optional[str] = None
    email_verification_otp_expires_at: Optional[datetime] = None

    # Security fields
    login_otp: Optional[str] = None
    login_otp_expires_at: Optional[datetime] = None
    reset_password_otp: Optional[str] = None
    reset_password_otp_expires_at: Optional[datetime] = None

    # Course and exam related
    enrolled_courses: List[str] = []
    preferred_exam_categories: List[ExamCategory] = []

    # Dashboard customization
    dashboard_settings: Dict[str, Any] = {}
    exam_category_preferences: Dict[str, Dict[str, Any]] = (
        {}
    )  # Settings per exam category
    ui_preferences: Dict[str, Any] = {"theme": "light", "layout": "standard"}

    # Payment and access
    purchased_test_series: List[str] = []
    purchased_materials: List[str] = []  # IDs of purchased study materials
    has_premium_access: bool = False

    # Test history and progress
    test_progress: Dict[str, Any] = {}  # For test continuation
    completed_tests: List[str] = []

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_login: Optional[datetime] = None

    class Settings:
        name = "users"

    def update_timestamp(self):
        self.updated_at = datetime.now(timezone.utc)
