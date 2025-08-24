from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from beanie import Document
from pydantic import Field, BaseModel
from enum import Enum


class PerformanceLevel(str, Enum):
    EXCELLENT = "excellent"  # >90%
    GOOD = "good"  # 70-90%
    AVERAGE = "average"  # 50-70%
    NEEDS_WORK = "needs_work"  # <50%


class StudyHabit(BaseModel):
    """Tracks study patterns and habits"""

    avg_session_minutes: float = 0
    sessions_per_week: float = 0
    most_active_day: Optional[str] = None  # Day of week
    most_active_time: Optional[str] = None  # Time of day
    consistency_score: float = 0  # Measure of regular study
    last_30_day_activity: List[Dict[str, Any]] = []  # Day by day activity


class UserAnalytics(Document):
    user_id: str

    # Aggregated performance
    tests_taken: int = 0
    total_questions_attempted: int = 0
    correct_answers: int = 0
    avg_accuracy: float = 0
    total_study_time_minutes: int = 0
    total_practice_questions: int = 0

    # Test performance
    avg_percentile: float = 0  # Average percentile across tests
    best_percentile: float = 0  # Best percentile achieved
    test_completion_rate: float = 0  # % of started tests completed
    avg_test_score: float = 0  # Average score percentage
    tests_passed: int = 0

    # Performance by subject
    subject_performance: Dict[str, Dict[str, float]] = (
        {}
    )  # {"Physics": {"accuracy": 0.8, "attempts": 100}}
    strongest_subjects: List[str] = []
    weakest_subjects: List[str] = []

    # Performance by difficulty
    difficulty_performance: Dict[str, Dict[str, float]] = (
        {}
    )  # {"easy": {"accuracy": 0.9, "attempts": 50}}
    difficulty_progression: List[Dict[str, Any]] = (
        []
    )  # Tracking improvement at each difficulty

    # Performance history
    performance_timeline: List[Dict[str, Any]] = (
        []
    )  # [{"date": datetime, "accuracy": 0.85, "questions": 20}]
    recent_activity: List[Dict[str, Any]] = []  # Last 10 activities

    # Study habits and patterns
    study_habits: StudyHabit = Field(default_factory=StudyHabit)

    # Material engagement
    materials_accessed: int = 0
    materials_completed: int = 0
    notes_downloads: int = 0
    video_watch_minutes: int = 0

    # Exam readiness
    exam_readiness: Dict[str, Dict[str, Any]] = (
        {}
    )  # {"NEET": {"readiness": 0.75, "weak_areas": ["Organic Chemistry"]}}

    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "user_analytics"

    def update_timestamp(self):
        self.last_updated = datetime.now(timezone.utc)
