from typing import List, Optional, AsyncIterator
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, status, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
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
from .routers.courses import courses_router
from .routers.tests import router as tests_router
from .routers.contact import router as contact_router
from .routers.materials import router as materials_router
from .routers.analytics import router as analytics_router
from .routers.exam_content import router as examcontent_router
from .routers.payment import router as payment_router
from .routers.enrollment import router as enrollment_router


# from .routers.exam_categories import router as exam_categories_router


# Security
security = HTTPBearer()


# Lifespan context manager for startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Startup - Initialize database connection for serverless
    print("⚡ Initializing database connection...")
    try:
        # Initialize Beanie models - this is idempotent and serverless-safe
        from .db import init_db
        await init_db()
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"⚠️ Database initialization warning: {str(e)}")
        # Don't fail startup in serverless - let endpoints handle connection issues

    yield  # App runs here

    # Shutdown - In serverless, connections are automatically cleaned up
    # No need to explicitly close connections as they're per-request in serverless
    print("✅ Serverless function completed")


# Initialize FastAPI app with lifespan
app = FastAPI(
    title="Pariksha Path API",
    description="Backend API for Pariksha Path",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
origins = [
    "http://localhost:3000",  # Your local frontend
    "http://localhost:5173",  # Vite dev server
    "https://pariksha-path2-0.vercel.app",  # Your production frontend
    "*",  # Allow all origins for development (remove in production)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Enhanced middleware for serverless environments to ensure database connectivity
@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    # Skip DB initialization for static assets and health checks
    if request.url.path.startswith(("/static/", "/favicon.ico", "/health")):
        return await call_next(request)

    # For API routes that need database access, ensure connection is ready
    if request.url.path.startswith(("/api/")):
        try:
            # Import here to avoid circular imports
            from .db import get_db_client

            # Get client and log attempt - simplified for serverless
            start_time = datetime.now()
            client = await get_db_client()

            # Quick ping test with timeout to verify connection is working
            try:
                await client.admin.command("ping", serverSelectionTimeoutMS=1000)
            except Exception as e:
                print(f"⚠️ DB ping check failed but continuing: {str(e)}")
                # Don't fail the request - let the endpoint handle DB errors

            # Log connection time for monitoring
            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            print(f"✓ DB connection ready in {elapsed:.2f}ms")

        except Exception as e:
            # Log error but don't fail the request yet
            # Let the actual endpoint handle DB errors appropriately
            print(f"❌ DB connection middleware error: {str(e)}")

    # Continue with the request
    response = await call_next(request)
    return response


# Include routers
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(courses_router)
# app.include_router(exam_categories_router)
app.include_router(tests_router)
app.include_router(materials_router)
app.include_router(analytics_router)
# app.include_router(content_router)
app.include_router(contact_router)
app.include_router(analytics_router)
app.include_router(payment_router)
app.include_router(enrollment_router)
app.include_router(examcontent_router)

# Health check endpoints
@app.get("/")
async def root():
    return {"message": "Coaching Institute API is running!", "status": "healthy"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "coaching-api"}


@app.get("/api/v1/db-health")
async def db_health_check():
    """Check MongoDB connection health - useful for diagnosing connection issues"""
    try:
        # Import here to avoid circular imports
        from .db import get_db_client

        # Get client and measure connection time
        start_time = datetime.now()
        client = await get_db_client()
        client_time = (datetime.now() - start_time).total_seconds() * 1000

        # Test with a ping command
        ping_start = datetime.now()
        await client.admin.command("ping")
        ping_time = (datetime.now() - ping_start).total_seconds() * 1000

        # Get server info
        server_info = await client.admin.command("serverStatus")
        connection_info = server_info.get("connections", {})

        return {
            "status": "connected",
            "timing": {
                "client_init_ms": round(client_time, 2),
                "ping_ms": round(ping_time, 2),
                "total_ms": round(client_time + ping_time, 2),
            },
            "connections": {
                "current": connection_info.get("current"),
                "available": connection_info.get("available"),
                "total_created": connection_info.get("totalCreated"),
            },
            "server_time": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__,
            "server_time": datetime.now().isoformat(),
        }


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

        query_filters = {"is_active": True}

        if category:
            query_filters["category"] = category

        if is_free is not None:
            query_filters["is_free"] = is_free

        if search:
            query_filters["$or"] = [
                {"title": {"$regex": search, "$options": "i"}},
                {"description": {"$regex": search, "$options": "i"}},
            ]

        skip = (page - 1) * limit

        sort_direction = 1 if sort_order == "asc" else -1

        try:
            courses = (
                await Course.find(query_filters)
                .sort([(sort_by, sort_direction)])
                .skip(skip)
                .limit(limit)
                .to_list()
            )

            total_courses = await Course.find(query_filters).count()
            total_pages = (total_courses + limit - 1) // limit

            course_list = []

            for course in courses:
                try:
                    course_data = {
                        "id": str(course.id),
                        "title": course.title,
                        "code": course.code,
                        "category": course.category.value,
                        "sub_category": course.sub_category,
                        "description": course.description,
                        "sections": getattr(course, "sections", []),
                        "price": course.price,
                        "is_free": course.is_free,
                        "discount_percent": course.discount_percent,
                        "thumbnail_url": course.thumbnail_url,
                        "material_count": len(getattr(course, "material_ids", [])),
                        "test_series_count": len(
                            getattr(course, "test_series_ids", [])
                        ),
                        "enrolled_students_count": getattr(
                            course, "enrolled_students_count", 0
                        ),
                    }
                    course_list.append(course_data)
                except Exception as e:

                    import traceback

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
            import traceback

            raise

    except Exception as e:
        import traceback

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve courses: {str(e)}",
        )


# Admin routes - Admin only
@app.get("/api/v1/admin/dashboard")
async def admin_dashboard(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )

    try:
        total_users = await User.find({"role": UserRole.STUDENT}).count()
        active_users = await User.find(
            {"role": UserRole.STUDENT, "is_active": True}
        ).count()

        total_courses = await Course.find().count()
        active_courses = await Course.find({"is_active": True}).count()

        total_tests = await TestSeries.find().count()
        total_attempts = await TestAttempt.find().count()

        total_materials = await StudyMaterial.find().count()

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

        exam_categories = {}
        for category in ExamCategory:
            count = await User.find({"preferred_exam_categories": category}).count()
            exam_categories[category.value] = count

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
            "materials": {"total": total_materials},
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


# Dev-only routes
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
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
