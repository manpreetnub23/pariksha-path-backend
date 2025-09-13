from typing import List, Optional, Dict, Any
from enum import Enum
from .base import BaseDocument


class QuestionType(str, Enum):
    MCQ = "mcq"
    FILL_BLANK = "fill_blank"
    TRUE_FALSE = "true_false"
    NUMERICAL = "numerical"


class DifficultyLevel(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Question(BaseDocument):
    # Basic info
    title: str
    question_text: str
    question_type: QuestionType
    difficulty_level: DifficultyLevel

    # Classification
    course_id: str  # Reference to the course/exam this question belongs to
    section: str  # Section within the course (e.g., "Physics", "Chemistry")
    exam_year: Optional[int] = None  # For PYQs, null for current year

    # Content - Updated to support multiple correct answers
    options: List[Dict] = []  # [{"text": "Option text", "is_correct": bool}]
    explanation: Optional[str] = None
    remarks: Optional[str] = None
    # Metadata
    subject: str  # e.g., "Physics", "Chemistry", "Mathematics"
    topic: str  # e.g., "Mechanics", "Organic Chemistry"
    tags: List[str] = []

    # Indexes for faster querying
    class Settings:
        indexes = [
            [
                ("course_id", 1),
                ("section", 1),
            ],  # Compound index for course+section queries
            "subject",
            "topic",
        ]

    metadata: Optional[Dict[str, Any]] = (
        {}
    )  # For storing additional data like image URLs
    # Admin info
    created_by: str  # Admin user ID

    class Settings:
        name = "questions"
