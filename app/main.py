from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from contextlib import asynccontextmanager
from datetime import datetime

from pydantic import BaseModel
from .db import init_db
import uvicorn
from .models.user import User
from .models.enums import UserRole, ExamCategory
from .routers.auth import router as auth_router
from .dependencies import get_current_user
from .routers.admin import router as admin_router


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


# Course routes (placeholder) - Protected
@app.get("/api/v1/courses")
async def get_courses(current_user: User = Depends(get_current_user)):
    """Get all available courses"""
    # TODO: Implement courses listing
    return {
        "message": "Courses endpoint - to be implemented",
        "user": current_user.name,
    }


# Mock test routes (placeholder) - Protected
@app.get("/api/v1/tests")
async def get_mock_tests(current_user: User = Depends(get_current_user)):
    """Get available mock tests"""
    # TODO: Implement mock tests listing
    return {
        "message": "Mock tests endpoint - to be implemented",
        "user": current_user.name,
    }


# Admin routes (placeholder) - Admin only
@app.get("/api/v1/admin/dashboard")
async def admin_dashboard(current_user: User = Depends(get_current_user)):
    """Admin dashboard data"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )

    # TODO: Implement admin dashboard
    return {
        "message": "Admin dashboard endpoint - to be implemented",
        "admin": current_user.name,
    }


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
