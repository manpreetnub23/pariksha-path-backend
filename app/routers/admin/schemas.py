"""
Pydantic schemas for admin endpoints
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field

from ...models.enums import UserRole, ExamCategory
from ...models.question import QuestionType, DifficultyLevel


# Student Management Schemas
class StudentUpdateRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None
    preferred_exam_categories: Optional[List[ExamCategory]] = None
    is_verified: Optional[bool] = None


class StudentResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    phone: str
    role: str
    is_active: bool
    is_verified: bool
    is_email_verified: bool
    preferred_exam_categories: List[str]
    enrolled_courses: List[str]
    created_at: datetime
    last_login: Optional[datetime] = None


class StudentFilterParams(BaseModel):
    search: Optional[str] = None
    exam_category: Optional[ExamCategory] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    sort_by: Optional[str] = "created_at"
    sort_order: Optional[str] = "desc"


class PasswordResetRequest(BaseModel):
    new_password: str


# Question Management Schemas
class OptionModel(BaseModel):
    text: str
    is_correct: bool
    order: int = 0


class QuestionCreateRequest(BaseModel):
    title: str
    question_text: str
    question_type: QuestionType
    difficulty_level: DifficultyLevel
    exam_type: str
    exam_year: Optional[int] = None
    options: List[OptionModel]
    explanation: Optional[str] = None
    remarks: Optional[str] = None
    subject: str
    topic: str
    tags: List[str] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Newton's First Law",
                "question_text": "What is Newton's First Law of Motion?",
                "question_type": "mcq",
                "difficulty_level": "medium",
                "exam_type": "JEE Main",
                "exam_year": 2023,
                "options": [
                    {
                        "text": "An object at rest stays at rest unless acted upon by an external force.",
                        "is_correct": True,
                    },
                    {
                        "text": "Force equals mass times acceleration.",
                        "is_correct": False,
                    },
                    {
                        "text": "For every action, there is an equal and opposite reaction.",
                        "is_correct": False,
                    },
                    {
                        "text": "Energy can neither be created nor destroyed.",
                        "is_correct": False,
                    },
                ],
                "explanation": "Newton's First Law states that an object will remain at rest or in uniform motion in a straight line unless acted upon by an external force.",
                "subject": "Physics",
                "topic": "Mechanics",
                "tags": ["newton", "motion", "laws"],
            }
        }


class QuestionUpdateRequest(BaseModel):
    title: Optional[str] = None
    question_text: Optional[str] = None
    question_type: Optional[QuestionType] = None
    difficulty_level: Optional[DifficultyLevel] = None
    exam_year: Optional[int] = None
    options: Optional[List[OptionModel]] = None
    explanation: Optional[str] = None
    remarks: Optional[str] = None
    subject: Optional[str] = None
    topic: Optional[str] = None
    tags: Optional[List[str]] = Field(default=None)
    is_active: Optional[bool] = None


class QuestionResponse(BaseModel):
    id: str
    title: str
    question_text: str
    question_type: str
    difficulty_level: str
    exam_year: Optional[int]
    options: List[Dict[str, Any]]
    explanation: Optional[str]
    remarks: Optional[str]
    subject: str
    topic: str
    tags: List[str]
    is_active: bool
    created_by: str
    created_at: datetime
    updated_at: datetime


# CSV Import Schemas
class CSVImportRequest(BaseModel):
    test_title: str
    exam_category: str
    exam_subcategory: str
    subject: str
    topic: Optional[str] = None
    difficulty: str = "MEDIUM"
    duration_minutes: int = 60
    is_free: str = "false"
    existing_test_id: Optional[str] = None


# Common Response Schemas
class PaginationInfo(BaseModel):
    total: int
    page: int
    limit: int
    total_pages: int


class StandardResponse(BaseModel):
    message: str
    data: Optional[Any] = None
    pagination: Optional[PaginationInfo] = None
    changes: Optional[Dict[str, Any]] = None
