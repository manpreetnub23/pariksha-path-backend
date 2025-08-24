from datetime import datetime, timezone
from enum import Enum
from beanie import Document
from pydantic import Field


class ActionType(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class AdminAction(Document):
    admin_id: str
    action_type: ActionType
    target_collection: str  # e.g., "users", "questions"
    target_id: str  # ID of the affected document
    changes: dict = {}  # What was changed
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "admin_actions"
