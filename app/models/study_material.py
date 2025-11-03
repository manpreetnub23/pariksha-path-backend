from pydantic import Field, BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from .base import BaseDocument
from .enums import MaterialType, MaterialAccessType, MaterialCategory


class MaterialDownload(BaseModel):
    """Tracks individual downloads of study materials"""

    user_id: str
    download_time: datetime
    ip_address: Optional[str] = None
    device_info: Optional[Dict[str, Any]] = None


class StudyMaterial(BaseDocument):
    """Enhanced model for study materials with tracking"""

    title: str
    description: str

    # Content details
    format: MaterialType
    category: MaterialCategory
    file_url: str
    file_size_kb: int
    preview_url: Optional[str] = None  # For sample/preview

    # Classification
    access_type: MaterialAccessType = MaterialAccessType.PREMIUM
    exam_category: str  # Medical, Engineering, etc.
    exam_subcategory: Optional[str] = None  # NEET, JEE, etc.
    subject: str
    topic: Optional[str] = None
    tags: List[str] = []

    # Relationships
    course_ids: List[str] = []  # Associated courses

    # Stats
    download_count: int = 0
    view_count: int = 0
    rating: float = 0.0
    review_count: int = 0
    recent_downloads: List[MaterialDownload] = []

    # Admin
    created_by: str
    version: int = 1  # For tracking updates

    class Settings:
        name = "study_materials"

    def track_download(
        self,
        user_id: str,
        ip_address: Optional[str] = None,
        device_info: Optional[Dict[str, Any]] = None,
    ):
        """Track a new download of this material"""
        download = MaterialDownload(
            user_id=user_id,
            download_time=datetime.now(timezone.utc),
            ip_address=ip_address,
            device_info=device_info,
        )

        # Keep only recent downloads in the document
        if len(self.recent_downloads) >= 20:  # Limit to last 20
            self.recent_downloads.pop(0)

        self.recent_downloads.append(download)
        self.download_count += 1
        self.update_timestamp()


class UserMaterialProgress(BaseDocument):
    """Tracks user progress and interaction with study materials"""

    user_id: str
    material_id: str

    # Progress tracking
    first_accessed: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_accessed: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    download_count: int = 0
    view_count: int = 0
    completed: bool = False
    completion_percentage: float = 0  # For partial reading progress

    # User feedback
    user_rating: Optional[int] = None  # 1-5 stars
    user_notes: Optional[str] = None
    bookmarked: bool = False

    # If material has exercises/questions
    exercises_attempted: int = 0
    exercises_completed: int = 0

    class Settings:
        name = "user_material_progress"

    def update_access(self):
        """Update the last accessed timestamp"""
        self.last_accessed = datetime.now(timezone.utc)
        self.view_count += 1

    def update_completion(self, percentage: float):
        """Update completion percentage"""
        self.completion_percentage = percentage
        if percentage >= 100:
            self.completed = True
