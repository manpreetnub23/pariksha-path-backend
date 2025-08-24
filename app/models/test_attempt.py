from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from beanie import Document
from pydantic import Field, BaseModel
from enum import Enum


class AnswerStatus(str, Enum):
    CORRECT = "correct"
    INCORRECT = "incorrect"
    PARTIALLY_CORRECT = "partially_correct"
    SKIPPED = "skipped"


class QuestionAttempt(BaseModel):
    question_id: str
    selected_options: List[str] = []
    status: AnswerStatus
    time_spent_seconds: Optional[int] = None
    marks_awarded: float = 0
    marks_available: float
    negative_marks: float = 0  # If applicable


class SectionSummary(BaseModel):
    section_name: str
    total_questions: int
    attempted_questions: int
    correct_answers: int
    marks_obtained: float
    max_marks: float
    accuracy_percent: float


class TestAttempt(Document):
    user_id: str
    test_series_id: str
    test_session_id: Optional[str] = (
        None  # Reference to TestSession for interface state
    )
    start_time: datetime
    end_time: Optional[datetime] = None

    # Detailed question attempts
    question_attempts: List[QuestionAttempt] = []

    # Section-wise performance (if test has sections)
    section_summaries: List[SectionSummary] = []

    # Analysis metrics
    total_questions: int
    attempted_questions: int = 0
    correct_answers: int = 0
    score: float = 0
    max_score: float
    accuracy: float = 0
    time_spent_seconds: int = 0
    is_completed: bool = False
    passed: Optional[bool] = None  # Based on passing criteria

    # Percentile (calculated after sufficient attempts)
    percentile: Optional[float] = None
    rank: Optional[int] = None

    # Enhanced analytics
    subject_wise_performance: Dict[str, Dict[str, Any]] = (
        {}
    )  # {"Physics": {"score": 10, "max": 15}}
    topic_wise_performance: Dict[str, Dict[str, Any]] = (
        {}
    )  # {"Mechanics": {"score": 5, "max": 10}}
    difficulty_performance: Dict[str, Dict[str, Any]] = (
        {}
    )  # {"easy": {"accuracy": 0.9}}
    strengths: List[str] = []  # Topics with high performance
    weaknesses: List[str] = []  # Topics needing improvement

    # Review status
    is_reviewed: bool = False
    reviewed_at: Optional[datetime] = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "test_attempts"

    def update_timestamp(self):
        self.updated_at = datetime.now(timezone.utc)

    def calculate_metrics(self):
        """Calculate performance metrics based on question attempts"""
        if not self.question_attempts:
            return

        self.attempted_questions = sum(
            1 for q in self.question_attempts if q.selected_options
        )
        self.correct_answers = sum(
            1 for q in self.question_attempts if q.status == AnswerStatus.CORRECT
        )

        total_score = sum(
            q.marks_awarded - q.negative_marks for q in self.question_attempts
        )
        self.score = max(0, total_score)  # Ensure score is not negative

        if self.attempted_questions > 0:
            self.accuracy = round(self.correct_answers / self.attempted_questions, 2)
