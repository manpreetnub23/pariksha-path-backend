from beanie import Document
from pydantic import Field
from typing import List, Optional
from datetime import datetime, timezone
from enum import Enum


class BlogCategory(str, Enum):
    NOTIFICATION = "notification"
    SYLLABUS = "syllabus"
    STRATEGY = "strategy"
    MOTIVATION = "motivation"
    NEWS = "news"


class Blog(Document):
    title: str
    slug: str  # URL-friendly version of title
    content: str
    summary: str

    # Organization
    category: BlogCategory
    tags: List[str] = []
    exam_related: Optional[List[str]] = []  # Related exams

    # Media
    featured_image: Optional[str] = None
    additional_images: List[str] = []

    # SEO
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    keywords: List[str] = []

    # Stats
    view_count: int = 0

    # Admin
    author_id: str
    is_published: bool = False
    published_date: Optional[datetime] = None

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "blogs"

    def update_timestamp(self):
        self.updated_at = datetime.now(timezone.utc)

    def publish(self):
        self.is_published = True
        self.published_date = datetime.now(timezone.utc)
