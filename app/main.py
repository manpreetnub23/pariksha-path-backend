from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from contextlib import asynccontextmanager
from datetime import datetime

from pydantic import BaseModel
from .db import init_db
import uvicorn
from .models.user import User
from .models.enums import UserRole, ExamCategory
from .models.course import Course
from .models.test import TestSeries, TestAttempt, TestSession
from .models.study_material import StudyMaterial
from .routers.auth import router as auth_router
from .dependencies import get_current_user
from .routers.admin import router as admin_router
from .routers.courses import router as courses_router
from .routers.exam_categories import router as exam_categories_router
from .routers.tests import router as tests_router
from .routers.materials import router as materials_router


# Security
security = HTTPBearer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup"""
    await init_db()
    print("Database initialized successfully!")
    yield


# Initialize FastAPI app
app = FastAPI(
    title="Pariksha Path API",
    description="Backend API for Pariksha Path",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
origins = [
    "http://localhost:3000",  # Your local frontend
    "https://pariksha-path2-0.vercel.app/",  # Your production frontend
    # Add any other frontend URLs you need
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(courses_router)
app.include_router(exam_categories_router)
app.include_router(tests_router)
app.include_router(materials_router)


# Health check endpoints
@app.get("/")
async def root():
    return {"message": "Coaching Institute API is running!", "status": "healthy"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "coaching-api"}


# API Routes Groups
@app.get("/api/v1/test")
async def test_endpoint():
    return {"message": "API v1 is working!"}


# Course routes - Protected
@app.get("/api/v1/courses")
async def get_courses(
    category: Optional[ExamCategory] = Query(
        None, description="Filter by exam category"
    ),
    search: Optional[str] = Query(None, description="Search in title and description"),
    is_free: Optional[bool] = Query(None, description="Filter by free courses"),
    sort_by: str = Query("priority_order", description="Field to sort by"),
    sort_order: str = Query("asc", description="Sort order (asc or desc)"),
    page: int = Query(1, description="Page number", ge=1),
    limit: int = Query(10, description="Items per page", ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    """Get all available courses with filtering and pagination"""
    try:
        # Build query filters
        query_filters = {"is_active": True}

        if category:
            query_filters["category"] = category

        if is_free is not None:
            query_filters["is_free"] = is_free

        if search:
            # Search in title or description
            query_filters["$or"] = [
                {"title": {"$regex": search, "$options": "i"}},
                {"description": {"$regex": search, "$options": "i"}},
            ]

        # Calculate pagination
        skip = (page - 1) * limit

        # Set sort order
        sort_direction = 1 if sort_order == "asc" else -1

        # Fetch courses
        courses = (
            await Course.find(query_filters)
            .sort([(sort_by, sort_direction)])
            .skip(skip)
            .limit(limit)
            .to_list()
        )

        # Count total matching courses for pagination info
        total_courses = await Course.find(query_filters).count()
        total_pages = (total_courses + limit - 1) // limit

        # Format response
        course_list = []
        for course in courses:
            course_list.append(
                {
                    "id": str(course.id),
                    "title": course.title,
                    "code": course.code,
                    "category": course.category.value,
                    "sub_category": course.sub_category,
                    "description": course.description,
                    "price": course.price,
                    "is_free": course.is_free,
                    "discount_percent": course.discount_percent,
                    "thumbnail_url": course.thumbnail_url,
                    "material_count": len(course.material_ids),
                    "test_series_count": len(course.test_series_ids),
                    "enrolled_students_count": course.enrolled_students_count,
                }
            )

        return {
            "message": "Courses retrieved successfully",
            "courses": course_list,
            "pagination": {
                "total": total_courses,
                "page": page,
                "limit": limit,
                "total_pages": total_pages,
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve courses: {str(e)}",
        )


# Removed: Mock test routes are now handled by the tests router


# Admin routes - Admin only
@app.get("/api/v1/admin/dashboard")
async def admin_dashboard(current_user: User = Depends(get_current_user)):
    """Admin dashboard data with key metrics and statistics"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )

    try:
        # Get user statistics
        total_users = await User.find({"role": UserRole.STUDENT}).count()
        active_users = await User.find(
            {"role": UserRole.STUDENT, "is_active": True}
        ).count()

        # Get course statistics
        total_courses = await Course.find().count()
        active_courses = await Course.find({"is_active": True}).count()

        # Get test statistics
        total_tests = await TestSeries.find().count()
        total_attempts = await TestAttempt.find().count()

        # Get material statistics
        total_materials = await StudyMaterial.find().count()

        # Get recent users (last 5 registered)
        recent_users = (
            await User.find({"role": UserRole.STUDENT})
            .sort([("created_at", -1)])
            .limit(5)
            .to_list()
        )
        recent_users_data = [
            {
                "id": str(user.id),
                "name": user.name,
                "email": user.email,
                "created_at": user.created_at,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
            }
            for user in recent_users
        ]

        # Get recent test attempts
        recent_attempts = (
            await TestAttempt.find().sort([("created_at", -1)]).limit(5).to_list()
        )
        recent_attempts_data = []

        for attempt in recent_attempts:
            user = await User.get(attempt.user_id)
            test = await TestSeries.get(attempt.test_series_id)

            if user and test:
                recent_attempts_data.append(
                    {
                        "id": str(attempt.id),
                        "user_name": user.name,
                        "test_title": test.title,
                        "score": attempt.score,
                        "max_score": attempt.max_score,
                        "percentage": (
                            round((attempt.score / attempt.max_score) * 100, 2)
                            if attempt.max_score > 0
                            else 0
                        ),
                        "date": attempt.created_at,
                    }
                )

        # Get exam category distribution
        exam_categories = {}
        for category in ExamCategory:
            count = await User.find({"preferred_exam_categories": category}).count()
            exam_categories[category.value] = count

        # Compile dashboard data
        dashboard_data = {
            "users": {
                "total": total_users,
                "active": active_users,
                "inactive": total_users - active_users,
                "recent": recent_users_data,
            },
            "courses": {
                "total": total_courses,
                "active": active_courses,
                "inactive": total_courses - active_courses,
            },
            "tests": {
                "total": total_tests,
                "attempts": total_attempts,
                "recent_attempts": recent_attempts_data,
            },
            "materials": {
                "total": total_materials,
            },
            "exam_categories": exam_categories,
        }

        return {
            "message": "Admin dashboard data retrieved successfully",
            "admin": current_user.name,
            "dashboard": dashboard_data,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve dashboard data: {str(e)}",
        )


# Development Routes (keep for now, remove in production)
class UserCreateRequest(BaseModel):
    name: str
    email: str
    phone: str
    password_hash: str
    role: UserRole = UserRole.STUDENT
    is_active: bool = True
    is_verified: bool = False
    enrolled_courses: List[str] = []
    preferred_exam_categories: List[ExamCategory] = []
    purchased_test_series: List[str] = []
    has_premium_access: bool = False


class UserUpdateRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    enrolled_courses: Optional[List[str]] = None
    preferred_exam_categories: Optional[List[ExamCategory]] = None
    purchased_test_series: Optional[List[str]] = None
    has_premium_access: Optional[bool] = None


@app.post("/api/v1/dev/create_user")
async def create_user(user_data: UserCreateRequest):
    """Create a new user (Development only)"""
    try:
        existing_user = await User.find_one({"email": user_data.email})
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists",
            )
        new_user = User(**user_data.model_dump())
        await new_user.insert()
        return {
            "message": "User created successfully",
            "user_id": str(new_user.id),
            "user": {
                "id": str(new_user.id),
                "name": new_user.name,
                "email": new_user.email,
                "role": new_user.role,
                "created_at": new_user.created_at,
            },
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating user: {str(e)}",
        )


# 👇 Keep this at bottom of app/main.py
# Only run uvicorn locally, not in Vercel
if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

# # Vercel needs this (export app object)
# app = app
