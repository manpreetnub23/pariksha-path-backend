from typing import List, Optional
from datetime import datetime
from enum import Enum
from .base import BaseDocument


class BlogCategory(str, Enum):
    NOTIFICATION = "notification"
    SYLLABUS = "syllabus"
    STRATEGY = "strategy"
    MOTIVATION = "motivation"
    NEWS = "news"


class Blog(BaseDocument):
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

    class Settings:
        name = "blogs"

    def publish(self):
        self.is_published = True
        self.published_date = datetime.now()
