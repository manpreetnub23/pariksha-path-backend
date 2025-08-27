"""
Unified test module containing all test-related models and shared components.
This module organizes the test lifecycle models while maintaining separation of concerns.
"""

from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Any, Union
from pydantic import Field, BaseModel
from enum import Enum
from .base import BaseDocument


# ================ Shared Enums and Types ================


class TestDifficulty(str, Enum):
    """Difficulty levels for tests"""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    MIXED = "mixed"


class NavigationMode(str, Enum):
    """Navigation modes for test interface"""

    LINEAR = "linear"  # Must complete questions in order
    FLEXIBLE = "flexible"  # Can navigate freely between questions


class AnswerStatus(str, Enum):
    """Status of an answer in a test attempt"""

    CORRECT = "correct"
    INCORRECT = "incorrect"
    PARTIALLY_CORRECT = "partially_correct"
    SKIPPED = "skipped"


# ================ Shared Components ================


class TestSection(BaseModel):
    """Section within a test"""

    name: str
    description: Optional[str] = None
    question_ids: List[str] = []
    total_marks: float = 0
    order: int = 0


class QuestionAttempt(BaseModel):
    """User's attempt at a question"""

    question_id: str
    selected_options: List[str] = []
    status: AnswerStatus
    time_spent_seconds: Optional[int] = None
    marks_awarded: float = 0
    marks_available: float
    negative_marks: float = 0  # If applicable


class SectionSummary(BaseModel):
    """Performance summary for a test section"""

    section_name: str
    total_questions: int
    attempted_questions: int
    correct_answers: int
    marks_obtained: float
    max_marks: float
    accuracy_percent: float


class TestInterfaceConfig(BaseModel):
    """Configuration for test UI and behavior"""

    # Timer settings
    show_timer: bool = True
    timer_warning_threshold: int = 300  # Seconds remaining for warning
    timer_placement: str = "top_right"

    # Question display
    show_question_numbers: bool = True
    show_marks_per_question: bool = True
    enable_math_formatting: bool = False

    # Navigation
    navigation_mode: NavigationMode = NavigationMode.FLEXIBLE
    confirm_on_question_change: bool = False
    enable_question_flagging: bool = True

    # Submission
    confirm_on_submit: bool = True
    show_results_immediately: bool = False
    auto_submit_on_timeout: bool = True

    # Review
    enable_review_screen: bool = True
    show_answers_after_submit: bool = False

    # Appearance
    theme: str = "default"
    font_size: str = "medium"


# ================ Main Models ================


class TestSeries(BaseDocument):
    """
    Model for test series - represents the test definition/template
    with questions, configuration, and metadata.
    """

    # Basic info
    title: str
    description: str

    # Classification
    exam_category: str  # Medical, Engineering, etc.
    exam_subcategory: Optional[str] = None  # NEET, JEE Main, etc.
    subject: Optional[str] = None  # For subject-specific tests

    # Test configuration
    total_questions: int
    duration_minutes: int
    max_score: int
    passing_percentage: float = 33.0
    difficulty: TestDifficulty = TestDifficulty.MEDIUM

    # Question organization
    question_ids: List[str] = []  # References to questions
    sections: List[TestSection] = []  # Optional sections with their questions

    # Access control
    is_active: bool = True
    is_free: bool = False
    price: Optional[float] = None  # If individually purchasable

    # Display info
    thumbnail_url: Optional[str] = None
    instructions: Optional[str] = None

    # Default interface configuration
    default_interface_config: TestInterfaceConfig = Field(
        default_factory=TestInterfaceConfig
    )

    # Stats
    attempt_count: int = 0
    avg_score: float = 0

    # Admin
    created_by: str

    class Settings:
        name = "test_series"

    def update_stats(self, new_score: float):
        """Update average score when a new attempt is made"""
        if self.attempt_count == 0:
            self.avg_score = new_score
        else:
            # Calculate new average
            total = self.avg_score * self.attempt_count
            self.avg_score = (total + new_score) / (self.attempt_count + 1)

        self.attempt_count += 1
        self.update_timestamp()


class TestSession(BaseDocument):
    """
    Tracks an active test session with interface state.
    This is ephemeral and exists only during an active test-taking session.
    """

    user_id: str
    test_series_id: str
    attempt_id: str  # Reference to TestAttempt

    # Session timing
    start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expected_end_time: datetime
    actual_end_time: Optional[datetime] = None

    # State tracking
    current_question_index: int = 0
    flagged_questions: List[int] = []
    visited_questions: List[int] = []
    time_spent_per_question: Dict[int, int] = {}  # Question index -> seconds

    # Interface config
    interface_config: TestInterfaceConfig

    # Session state
    is_active: bool = True
    is_paused: bool = False
    pause_time: Optional[datetime] = None
    total_pause_duration: int = 0  # In seconds

    # Session events
    events: List[Dict[str, Any]] = []  # Track user actions during test

    class Settings:
        name = "test_sessions"

    def calculate_remaining_time(self) -> int:
        """Calculate remaining time in seconds, accounting for pauses"""
        now = datetime.now(timezone.utc)

        # If paused, use the pause time for calculation
        reference_time = self.pause_time if self.is_paused else now

        elapsed = (
            reference_time - self.start_time
        ).total_seconds() - self.total_pause_duration
        allocated = (self.expected_end_time - self.start_time).total_seconds()
        remaining = max(0, allocated - elapsed)

        return int(remaining)

    def pause(self):
        """Pause the test timer"""
        if not self.is_paused:
            self.is_paused = True
            self.pause_time = datetime.now(timezone.utc)
            self.events.append(
                {
                    "type": "pause",
                    "timestamp": self.pause_time,
                    "question_index": self.current_question_index,
                }
            )

    def resume(self):
        """Resume the test timer"""
        if self.is_paused and self.pause_time:
            now = datetime.now(timezone.utc)
            pause_duration = int((now - self.pause_time).total_seconds())
            self.total_pause_duration += pause_duration

            self.is_paused = False
            self.events.append(
                {"type": "resume", "timestamp": now, "pause_duration": pause_duration}
            )

    def mark_complete(self):
        """Mark test as completed"""
        self.is_active = False
        self.actual_end_time = datetime.now(timezone.utc)
        self.events.append({"type": "complete", "timestamp": self.actual_end_time})


class TestAttempt(BaseDocument):
    """
    Represents a completed or in-progress attempt by a user,
    with answers and performance metrics.
    """

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

    class Settings:
        name = "test_attempts"

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

    def mark_complete(self, test_series: TestSeries):
        """Mark test attempt as complete and update related stats"""
        if not self.is_completed:
            self.is_completed = True
            self.end_time = datetime.now(timezone.utc)

            # Calculate final metrics
            self.calculate_metrics()

            # Determine if passed
            if self.max_score > 0:
                passing_score = (test_series.passing_percentage / 100) * self.max_score
                self.passed = self.score >= passing_score

            # Update test series stats
            test_series.update_stats(self.score)


# ================ Helper Functions ================


async def create_test_session(
    user_id: str, test_series_id: str
) -> tuple[TestSession, TestAttempt]:
    """
    Create a new test session and attempt for a user.

    Args:
        user_id: ID of the user taking the test
        test_series_id: ID of the test series

    Returns:
        Tuple of (TestSession, TestAttempt)
    """
    # Get the test series
    test_series = await TestSeries.get(test_series_id)
    if not test_series:
        raise ValueError(f"Test series with ID {test_series_id} not found")

    # Create test attempt
    attempt = TestAttempt(
        user_id=user_id,
        test_series_id=test_series_id,
        start_time=datetime.now(timezone.utc),
        total_questions=test_series.total_questions,
        max_score=test_series.max_score,
    )
    await attempt.insert()

    # Create test session
    session = TestSession(
        user_id=user_id,
        test_series_id=test_series_id,
        attempt_id=str(attempt.id),
        expected_end_time=datetime.now(timezone.utc)
        + timedelta(minutes=test_series.duration_minutes),
        interface_config=test_series.default_interface_config,
    )
    await session.insert()

    # Update attempt with session ID
    attempt.test_session_id = str(session.id)
    await attempt.save()

    return session, attempt


async def get_test_with_attempt_stats(
    test_id: str, user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get test details with attempt statistics.

    Args:
        test_id: ID of the test
        user_id: Optional user ID to get user-specific attempt stats

    Returns:
        Dictionary with test details and stats
    """
    test = await TestSeries.get(test_id)
    if not test:
        raise ValueError(f"Test with ID {test_id} not found")

    result = {
        "id": str(test.id),
        "title": test.title,
        "description": test.description,
        "exam_category": test.exam_category,
        "exam_subcategory": test.exam_subcategory,
        "total_questions": test.total_questions,
        "duration_minutes": test.duration_minutes,
        "max_score": test.max_score,
        "passing_percentage": test.passing_percentage,
        "difficulty": test.difficulty,
        "is_free": test.is_free,
        "attempt_count": test.attempt_count,
        "avg_score": test.avg_score,
    }

    # Add user-specific stats if user_id provided
    if user_id:
        # Get user's attempts for this test
        user_attempts = (
            await TestAttempt.find(
                {"user_id": user_id, "test_series_id": test_id, "is_completed": True}
            )
            .sort([("created_at", -1)])
            .to_list()
        )

        if user_attempts:
            best_attempt = max(user_attempts, key=lambda x: x.score)
            result["user_stats"] = {
                "attempts_count": len(user_attempts),
                "best_score": best_attempt.score,
                "best_score_percentage": (
                    round((best_attempt.score / best_attempt.max_score) * 100, 2)
                    if best_attempt.max_score > 0
                    else 0
                ),
                "last_attempt_date": user_attempts[0].end_time,
                "has_passed": any(
                    attempt.passed
                    for attempt in user_attempts
                    if attempt.passed is not None
                ),
            }
        else:
            result["user_stats"] = {
                "attempts_count": 0,
                "has_attempted": False,
            }

    return result
