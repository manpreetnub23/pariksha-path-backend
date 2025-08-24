from beanie import Document
from pydantic import Field, BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone


class Topic(BaseModel):
    """Individual topic within a unit"""

    name: str
    description: Optional[str] = None
    estimated_hours: Optional[int] = None
    is_important: bool = False
    material_ids: List[str] = []  # References to study materials
    question_ids: List[str] = []  # References to practice questions
    tags: List[str] = []


class Unit(BaseModel):
    """Unit containing multiple topics"""

    name: str
    description: Optional[str] = None
    topics: List[Topic] = []
    order: int  # Display order in syllabus
    estimated_hours: Optional[int] = None
    is_free: bool = False  # Whether this unit is available in free preview


class Syllabus(Document):
    """Comprehensive syllabus structure for courses"""

    title: str
    course_id: str  # Associated course
    description: str

    # Structure
    units: List[Unit] = []
    total_estimated_hours: Optional[int] = None

    # Categorization
    exam_category: str  # Medical, Engineering, etc.
    exam_subcategory: str  # NEET, JEE Main, etc.

    # Learning path
    prerequisites: List[str] = []  # Prerequisite course IDs or skills
    learning_outcomes: List[str] = []  # What students will learn

    # Progress tracking
    completion_criteria: Dict[str, Any] = {}  # Rules for marking complete

    # Access control
    is_published: bool = False

    # Admin
    created_by: str
    is_active: bool = True

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "syllabi"

    def update_timestamp(self):
        self.updated_at = datetime.now(timezone.utc)

    def calculate_total_hours(self):
        """Calculate the total estimated hours from all units"""
        total = 0
        for unit in self.units:
            if unit.estimated_hours:
                total += unit.estimated_hours
            else:
                # Sum up topic hours if unit hours not specified
                for topic in unit.topics:
                    if topic.estimated_hours:
                        total += topic.estimated_hours
        self.total_estimated_hours = total
        return total
