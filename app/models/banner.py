from beanie import Document 
from pydantic import Field
from typing import Optional
from datetime import datetime


class Banner(Document):
    title: Optional[str] = None
    image_url: str
    is_active: bool = True
    position: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "banners"   # collection name
