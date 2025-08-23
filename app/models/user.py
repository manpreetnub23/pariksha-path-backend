from beanie import Document
from pydantic import EmailStr, Field
from typing import List, Optional
from datetime import datetime, timezone
from enum import Enum


class UserRole(str, Enum):
    STUDENT = "student"
    ADMIN = "admin"


class ExamCategory(str, Enum):
    MEDICAL = "medical"  # NEET
    ENGINEERING = "engineering"  # JEE Main, JEE Advanced
    TEACHING = "teaching"  # HTET, CTET, DSSSB, KVS
    GOVT_EXAMS = "govt_exams"  # SSC CGL, CHSL, MTS, CPO, GD
    BANKING = "banking"  # IBPS PO, Clerk, SBI PO, RBI Assistant, NABARD
    DEFENCE = "defence"  # NDA, CDS, Airforce X/Y, Navy, Agniveer
    STATE_EXAMS = "state_exams"  # HSSC, HCS, Patwari, Police, Teachers


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

    # Course and exam related
    enrolled_courses: List[str] = []
    preferred_exam_categories: List[ExamCategory] = []

    # Payment and access
    purchased_test_series: List[str] = []
    has_premium_access: bool = False

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_login: Optional[datetime] = None

    class Settings:
        name = "users"

    def update_timestamp(self):
        self.updated_at = datetime.now(timezone.utc)
