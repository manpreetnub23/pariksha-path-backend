from beanie import Document
from pydantic import Field
from typing import List, Optional, Dict
from datetime import datetime, timezone
from enum import Enum


class QuestionType(str, Enum):
    MCQ = "mcq"
    FILL_BLANK = "fill_blank"
    TRUE_FALSE = "true_false"
    NUMERICAL = "numerical"


class DifficultyLevel(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Question(Document):
    # Basic info
    title: str
    question_text: str
    question_type: QuestionType
    difficulty_level: DifficultyLevel

    # Classification
    exam_type: str  # e.g., "NEET", "JEE Main", "SSC CGL"
    exam_year: Optional[int] = None  # For PYQs, null for current year

    # Content - Updated to support multiple correct answers
    options: List[Dict] = []  # [{"text": "Option text", "is_correct": bool}]
    explanation: Optional[str] = None

    # Metadata
    subject: str  # e.g., "Physics", "Chemistry", "Mathematics"
    topic: str  # e.g., "Mechanics", "Organic Chemistry"
    tags: List[str] = []

    # Admin info
    created_by: str  # Admin user ID
    is_active: bool = True

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "questions"

    def update_timestamp(self):
        self.updated_at = datetime.now(timezone.utc)
