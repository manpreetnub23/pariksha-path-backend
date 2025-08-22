from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager

from pydantic import BaseModel
from .db import init_db
import uvicorn
from .models.user import User, UserRole, ExamCategory


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
    title="Coaching Institute API",
    description="Backend API for Coaching Website & Exam Portal",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/")
async def root():
    return {"message": "Coaching Institute API is running!", "status": "healthy"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "coaching-api"}


# Authentication dependency (placeholder for now)
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Placeholder for JWT authentication
    Will be implemented when we add authentication routes
    """
    # TODO: Implement JWT token verification
    pass


# API Routes Groups
@app.get("/api/v1/test")
async def test_endpoint():
    return {"message": "API v1 is working!"}


# User management routes (placeholder structure)
@app.post("/api/v1/auth/register")
async def register_user():
    """User registration endpoint"""
    # TODO: Implement user registration
    return {"message": "Registration endpoint - to be implemented"}


@app.post("/api/v1/auth/login")
async def login_user():
    """User login endpoint"""
    # TODO: Implement user login with JWT
    return {"message": "Login endpoint - to be implemented"}


@app.get("/api/v1/auth/me")
async def get_current_user_info():
    """Get current user profile"""
    # TODO: Implement get current user
    return {"message": "User profile endpoint - to be implemented"}


# Course routes (placeholder)
@app.get("/api/v1/courses")
async def get_courses():
    """Get all available courses"""
    # TODO: Implement courses listing
    return {"message": "Courses endpoint - to be implemented"}


# Mock test routes (placeholder)
@app.get("/api/v1/tests")
async def get_mock_tests():
    """Get available mock tests"""
    # TODO: Implement mock tests listing
    return {"message": "Mock tests endpoint - to be implemented"}


# Admin routes (placeholder)
@app.get("/api/v1/admin/dashboard")
async def admin_dashboard():
    """Admin dashboard data"""
    # TODO: Implement admin dashboard
    return {"message": "Admin dashboard endpoint - to be implemented"}


# Dev only


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


# ___Development Routes____


@app.post("/api/v1/dev/create_user")
async def create_user(user_data: UserCreateRequest):
    """Create a new user"""
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


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
