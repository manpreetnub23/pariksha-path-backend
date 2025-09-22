"""
Admin router module
"""

from fastapi import APIRouter
from .students import router as students_router
from .questions import router as questions_router
from .csv_import import router as csv_import_router
from .admin_management import router as admin_management_router
from .images import router as images_router
from .sections import router as sections_router

# Create main admin router
router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])

# Include all sub-routers
router.include_router(students_router)
router.include_router(questions_router)
router.include_router(csv_import_router)
router.include_router(admin_management_router)
router.include_router(images_router)
router.include_router(sections_router)
