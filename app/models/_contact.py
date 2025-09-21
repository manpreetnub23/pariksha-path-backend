# from beanie import Document
# from pydantic import Field, EmailStr
# from typing import Optional
# from datetime import datetime, timezone
# from enum import Enum


# class ContactStatus(str, Enum):
#     PENDING = "pending"
#     IN_PROGRESS = "in_progress"
#     RESOLVED = "resolved"
#     SPAM = "spam"


# class ContactSource(str, Enum):
#     WEBSITE_FORM = "website_form"
#     WHATSAPP = "whatsapp"
#     EMAIL = "email"


# class Contact(Document):
#     name: str
#     email: EmailStr
#     phone: str
#     subject: str
#     message: str

#     # Source tracking
#     source: ContactSource = ContactSource.WEBSITE_FORM

#     # Admin processing
#     status: ContactStatus = ContactStatus.PENDING
#     assigned_to: Optional[str] = None  # Admin user ID
#     notes: Optional[str] = None  # Internal notes for admin
#     response_message: Optional[str] = None
#     responded_at: Optional[datetime] = None

#     # Timestamps
#     created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
#     updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

#     class Settings:
#         name = "contacts"

#     def update_timestamp(self):
#         self.updated_at = datetime.now(timezone.utc)

#     def mark_as_resolved(self, response_message: str):
#         self.status = ContactStatus.RESOLVED
#         self.response_message = response_message
#         self.responded_at = datetime.now(timezone.utc)
#         self.update_timestamp()


# class WhatsAppIntegration(Document):
#     """Configuration for WhatsApp business integration"""

#     admin_number: str  # Admin WhatsApp number
#     is_active: bool = True
#     webhook_url: Optional[str] = None
#     api_key: str
#     template_messages: dict = {}  # Predefined message templates

#     # Timestamps
#     created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
#     updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

#     class Settings:
#         name = "whatsapp_integration"

#     def update_timestamp(self):
#         self.updated_at = datetime.now(timezone.utc)
