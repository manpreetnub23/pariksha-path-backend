from datetime import datetime, timezone
from typing import Optional
from beanie import Document
from pydantic import Field


class BaseDocument(Document):
    """Base document class with common fields and methods"""

    # Status field
    is_active: bool = True

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        abstract = True  # Make this an abstract base class

    def update_timestamp(self):
        """Update the last modified timestamp"""
        self.updated_at = datetime.now(timezone.utc)
