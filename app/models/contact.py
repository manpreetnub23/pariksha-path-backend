from beanie import Document
from pydantic import Field, EmailStr
from typing import Optional
from datetime import datetime, timezone


class Contact(Document):
    name: str
    email: EmailStr
    phone: str
    message: str

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "contacts"

    def update_timestamp(self):
        self.updated_at = datetime.now(timezone.utc)
