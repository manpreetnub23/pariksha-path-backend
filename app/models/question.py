from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field
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


class QuestionOption(BaseModel):
    """Question option model"""

    text: str
    is_correct: bool
    order: int = 0


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

    # Content
    options: List[QuestionOption] = Field(default_factory=list)
    explanation: Optional[str] = None
    remarks: Optional[str] = None

    # Metadata
    subject: str  # e.g., "Physics", "Chemistry", "Mathematics"
    topic: str  # e.g., "Mechanics", "Organic Chemistry"
    tags: List[str] = Field(default_factory=list)

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

    metadata: Dict[str, Any] = Field(
        default_factory=dict
    )  # For storing additional data
    # Admin info
    created_by: str  # Admin user ID
