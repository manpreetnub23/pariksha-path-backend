from beanie import Document
from pydantic import Field, BaseModel
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta, timezone
from enum import Enum


class NavigationMode(str, Enum):
    LINEAR = "linear"  # Must complete questions in order
    FLEXIBLE = "flexible"  # Can navigate freely between questions


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


class TestSession(Document):
    """Tracks an active test session with interface state"""

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

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "test_sessions"

    def update_timestamp(self):
        self.updated_at = datetime.now(timezone.utc)

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
