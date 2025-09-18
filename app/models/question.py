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


class ImageAttachment(BaseModel):
    """Model for image attachments with metadata"""

    url: str
    alt_text: Optional[str] = None
    caption: Optional[str] = None
    order: int = 0  # For ordering multiple images
    file_size: Optional[int] = None  # In bytes
    dimensions: Optional[Dict[str, int]] = None  # {"width": 800, "height": 600}


class QuestionOption(BaseModel):
    """Enhanced option model with image support"""

    text: str
    is_correct: bool
    images: List[ImageAttachment] = []
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

    # Content with enhanced image support
    options: List[QuestionOption] = []  # Enhanced options with image support
    explanation: Optional[str] = None
    explanation_images: List[ImageAttachment] = []  # Images for explanation
    remarks: Optional[str] = None
    remarks_images: List[ImageAttachment] = []  # Images for remarks

    # Question text images
    question_images: List[ImageAttachment] = []  # Images for question text

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

    metadata: Optional[Dict[str, Any]] = {}  # For storing additional data
    # Admin info
    created_by: str  # Admin user ID

    class Settings:
        name = "questions"
