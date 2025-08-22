from beanie import Document
from datetime import datetime
from typing import Optional


class Course(Document):
    title: str
    category: str  # e.g. "Medical", "Engineering", "SSC"
    description: Optional[str]
    fee: Optional[float]
    syllabus: Optional[str]
    created_at: datetime = datetime.utcnow()

    class Settings:
        name = "courses"
