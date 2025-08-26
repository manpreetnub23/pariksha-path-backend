from datetime import datetime, timezone
from typing import Dict, List, Optional, Union
from beanie import Document
from pydantic import Field

# Define a recursive type for nested exam structure
ExamDict = Dict[
    str, Union[List[str], Dict[str, Union[List[str], Dict[str, List[str]]]]]
]


class ExamCategoryStructure(Document):
    """Model to store the hierarchical structure of exam categories and subcategories"""

    # The structure is stored as a nested dictionary that can have either lists or further dictionaries
    structure: ExamDict

    # Version tracking
    version: int = 1
    is_active: bool = True

    # Metadata
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "exam_category_structure"

    def update_timestamp(self):
        """Update the last modified timestamp"""
        self.updated_at = datetime.now(timezone.utc)
