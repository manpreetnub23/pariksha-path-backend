from beanie import Document
from pydantic import Field
from typing import Optional
from datetime import datetime, timezone, timedelta


class CourseEnrollment(Document):
    """Model for tracking individual user-course enrollment relationships with validity periods"""

    # References
    user_id: str  # ID of the enrolled user
    course_id: str  # ID of the enrolled course

    # Enrollment details
    enrolled_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None  # Calculated based on course validity period
    is_active: bool = True

    # Additional tracking
    enrollment_source: str = "manual"  # "manual", "payment", "admin_grant", etc.
    notes: Optional[str] = None  # Admin notes about this enrollment

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "course_enrollments"

    def update_timestamp(self):
        """Update the updated_at timestamp"""
        self.updated_at = datetime.now(timezone.utc)

    def is_expired(self) -> bool:
        """Check if the enrollment has expired"""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    def days_remaining(self) -> Optional[int]:
        """Get number of days remaining until expiration"""
        if not self.expires_at:
            return None
        if self.is_expired():
            return 0

        remaining = self.expires_at - datetime.now(timezone.utc)
        return max(0, remaining.days)

    def extend_validity(self, additional_days: int) -> None:
        """Extend the enrollment validity by additional days"""
        if not self.expires_at:
            # If no expiration date, don't set one
            return

        self.expires_at += timedelta(days=additional_days)
        self.update_timestamp()

    async def save(self, *args, **kwargs):
        """Override save to update timestamp"""
        self.update_timestamp()
        await super().save(*args, **kwargs)
