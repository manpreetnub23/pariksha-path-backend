# from datetime import datetime, timezone
# from typing import List, Optional, Dict, Any
# from pydantic import Field
# from enum import Enum
# from .base import BaseDocument
# from .enums import ExamCategory


# class TestDifficulty(str, Enum):
#     EASY = "easy"
#     MEDIUM = "medium"
#     HARD = "hard"
#     MIXED = "mixed"


# class TestSeries(BaseDocument):
#     """Model for test series"""

#     # Basic info
#     title: str
#     description: str

#     # Classification
#     exam_category: str  # Medical, Engineering, etc.
#     exam_subcategory: Optional[str] = None  # NEET, JEE Main, etc.
#     subject: Optional[str] = None  # For subject-specific tests

#     # Test configuration
#     total_questions: int
#     duration_minutes: int
#     max_score: int
#     passing_percentage: float = 33.0
#     difficulty: TestDifficulty = TestDifficulty.MEDIUM

#     # Question organization
#     question_ids: List[str] = []  # References to questions
#     sections: List[Dict[str, Any]] = []  # Optional sections with their questions

#     # Access control
#     is_free: bool = False
#     price: Optional[float] = None  # If individually purchasable

#     # Display info
#     thumbnail_url: Optional[str] = None
#     instructions: Optional[str] = None

#     # Stats
#     attempt_count: int = 0
#     avg_score: float = 0

#     # Admin
#     created_by: str

#     class Settings:
#         name = "test_series"

#     def update_stats(self, new_score: float):
#         """Update average score when a new attempt is made"""
#         if self.attempt_count == 0:
#             self.avg_score = new_score
#         else:
#             # Calculate new average
#             total = self.avg_score * self.attempt_count
#             self.avg_score = (total + new_score) / (self.attempt_count + 1)

#         self.attempt_count += 1
#         self.update_timestamp()
