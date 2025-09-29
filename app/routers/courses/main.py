"""
Main courses router - combines all course-related functionality
"""

from fastapi import APIRouter

# Import all the course sub-routers
from .crud import router as crud_router
from .sections import router as sections_router
from .materials import router as materials_router
from .mock_tests import router as mock_tests_router
from .mock_history import router as mock_history_router

# Create the main router that includes all sub-routers
router = APIRouter()

# Include all sub-routers
router.include_router(crud_router)
router.include_router(sections_router)
router.include_router(materials_router)
router.include_router(mock_tests_router)
router.include_router(mock_history_router)
