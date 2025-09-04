from beanie import Document
from pydantic import Field
from typing import List, Optional
from datetime import datetime, timezone
from enum import Enum


class NotificationType(str, Enum):
    GENERAL = "general"
    COURSE = "course"
    TEST = "test"
    PAYMENT = "payment"
    RESULT = "result"


class NotificationStatus(str, Enum):
    UNREAD = "unread"
    READ = "read"


class Notification(Document):
    user_id: str
    title: str
    message: str
    notification_type: NotificationType

    # References
    reference_id: Optional[str] = None  # ID of related item (course, test, etc.)
    reference_type: Optional[str] = None  # Type of reference (course, test, etc.)

    # Status
    status: NotificationStatus = NotificationStatus.UNREAD
    read_at: Optional[datetime] = None

    # Action
    action_url: Optional[str] = None  # Frontend URL to navigate to

    # Admin
    is_system_generated: bool = True
    created_by: Optional[str] = None  # Admin ID if manually created

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "notifications"

    def mark_as_read(self):
        self.status = NotificationStatus.READ
        self.read_at = datetime.now(timezone.utc)
