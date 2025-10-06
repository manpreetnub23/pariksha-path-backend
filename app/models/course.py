from beanie import Document
from pydantic import Field, BaseModel, validator
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from .enums import ExamCategory
import re
import uuid


class ExamSubCategory(BaseModel):
    """Specific exam within a category"""

    name: str  # e.g., "NEET", "JEE Main"
    description: Optional[str] = None
    icon_url: Optional[str] = None


class SectionFile(BaseModel):
    """Represents a file uploaded to a section"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    original_filename: str
    file_url: str
    file_size_kb: int
    file_type: str  # "pdf", "doc", "docx", etc.
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    uploaded_by: str  # Admin user ID
    description: Optional[str] = None
    is_active: bool = True


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

    # NEW: PDF and file management
    files: List[SectionFile] = Field(default_factory=list)

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

        # Handle case where v might be None or contain None values
        if v is None:
            return []

        # Filter out None values and empty strings
        filtered_sections = [s for s in v if s is not None and str(s).strip()]

        if not filtered_sections:
            return []

        # If sections are strings, convert them to Section objects
        if isinstance(filtered_sections[0], str):
            section_objects = []
            for i, section_name in enumerate(filtered_sections):
                section_objects.append(
                    Section(
                        name=section_name.strip(),
                        description=f"Section {i + 1}: {section_name}",
                        order=i + 1,
                        question_count=0,
                        is_active=True,
                    )
                )
            return section_objects

        return filtered_sections

    @validator("sections")
    def validate_section_names_unique(cls, v):
        if not v:
            return v

        # Handle both string sections and Section object sections
        if isinstance(v[0], str):
            # Sections are stored as strings
            names = [section.lower() for section in v]
        else:
            # Sections are Section objects
            names = [section.name.lower() for section in v]

        if len(names) != len(set(names)):
            raise ValueError("Section names must be unique (case-insensitive)")
        return v

    def get_section(self, section_name: str) -> Optional[Section]:
        """Get a section by name (case-insensitive)"""
        section_name = section_name.lower().strip()

        # Handle both string sections and Section object sections
        if isinstance(self.sections[0], str):
            # Sections are stored as strings
            for section in self.sections:
                if section.lower() == section_name:
                    return section  # Return the string section name
        else:
            # Sections are Section objects
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

    async def add_file_to_section(
        self, section_name: str, file_data: SectionFile
    ) -> bool:
        """Add a file to a specific section"""
        section = self.get_section(section_name)
        if not section:
            return False
        section.files.append(file_data)
        await self.save()
        return True

    async def remove_file_from_section(self, section_name: str, file_id: str) -> bool:
        """Remove a file from a specific section"""
        section = self.get_section(section_name)
        if not section:
            return False
        section.files = [f for f in section.files if f.id != file_id]
        await self.save()
        return True

    def get_section_files(self, section_name: str) -> List[SectionFile]:
        """Get all files for a specific section"""
        section = self.get_section(section_name)
        return section.files if section else []

    def get_section_file(
        self, section_name: str, file_id: str
    ) -> Optional[SectionFile]:
        """Get a specific file from a section"""
        section = self.get_section(section_name)
        if not section:
            return None
        for file in section.files:
            if file.id == file_id:
                return file
        return None

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
