from beanie import Document
from pydantic import Field, BaseModel, validator
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from .enums import ExamCategory


class ExamSubCategory(BaseModel):
    """Specific exam within a category"""

    name: str  # e.g., "NEET", "JEE Main"
    description: Optional[str] = None
    icon_url: Optional[str] = None


class Section(BaseModel):
    """Represents a section within a course"""

    name: str  # e.g., "Physics", "Chemistry"
    display_name: Optional[str] = (
        None  # Optional display name (e.g., "Physics for NEET")
    )
    description: Optional[str] = None
    question_count: int = 0  # Number of questions in this section
    order: int  # For sorting sections in the UI
    is_active: bool = True

    @validator("name")
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError("Section name cannot be empty")
        # Add any other validation rules for section names
        return v.strip()


class Course(Document):
    # Basic info
    title: str
    code: str  # Unique course code
    category: ExamCategory
    sub_category: str  # Specific exam (e.g., "NEET", "JEE Main")
    sections: List[Section] = []  # List of sections in this course

    # Content details
    description: str
    syllabus_id: Optional[str] = None  # Reference to detailed syllabus model

    @validator("sections", pre=True)
    def convert_string_sections_to_objects(cls, v):
        """Convert string sections to Section objects during migration"""
        if not v:
            return v

        # If sections are strings, convert them to Section objects
        if isinstance(v[0], str):
            section_objects = []
            for i, section_name in enumerate(v):
                section_objects.append(
                    Section(
                        name=section_name,
                        description=f"Section {i + 1}: {section_name}",
                        order=i + 1,
                        question_count=0,
                        is_active=True,
                    )
                )
            return section_objects

        return v

    @validator("sections")
    def validate_section_names_unique(cls, v):
        if not v:
            return v

        names = [section.name.lower() for section in v]
        if len(names) != len(set(names)):
            raise ValueError("Section names must be unique (case-insensitive)")
        return v

    def get_section(self, section_name: str) -> Optional[Section]:
        """Get a section by name (case-insensitive)"""
        section_name = section_name.lower().strip()
        for section in self.sections:
            if section.name.lower() == section_name:
                return section
        return None

    def get_section_names(self) -> List[str]:
        """Get list of section names (handles both string and Section object formats)"""
        if not self.sections:
            return []

        if isinstance(self.sections[0], str):
            return self.sections
        else:
            return [section.name for section in self.sections]

    async def add_section(self, section: Section) -> bool:
        """Add a new section to the course"""
        if self.get_section(section.name):
            return False  # Section already exists
        self.sections.append(section)
        await self.save()
        return True

    async def increment_question_count(self, section_name: str, count: int = 1) -> bool:
        """Increment the question count for a section"""
        section = self.get_section(section_name)
        if not section:
            return False
        section.question_count += count
        await self.save()
        return True

    # Pricing
    price: float
    is_free: bool = False
    discount_percent: Optional[float] = None

    # Resources
    material_ids: List[str] = []  # References to study materials
    test_series_ids: List[str] = []  # References to associated test series

    # Display info
    thumbnail_url: str
    icon_url: Optional[str] = None
    priority_order: int = 0  # For display ordering on frontend
    banner_url: Optional[str] = None  # Hero banner image
    tagline: Optional[str] = None  # Course tagline for marketing

    # Stats
    enrolled_students_count: int = 0

    # Status
    is_active: bool = True
    created_by: str  # Admin ID

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "courses"

    def update_timestamp(self):
        self.updated_at = datetime.now(timezone.utc)
