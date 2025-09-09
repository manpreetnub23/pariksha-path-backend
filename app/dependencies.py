from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .models.user import User
from .models.enums import UserRole
from .auth import AuthService
from .db import init_db

# Security setup
security = HTTPBearer()



async def ensure_db():
    """
    FastAPI dependency: call on routes/routers requiring DB.
    First call triggers init_beanie once; subsequent calls are cheap.
    """
    await init_db()

# Dependency to get current user
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """Get current user from JWT token"""
    return await AuthService.get_current_user(credentials.credentials)


# Admin-only middleware
async def admin_required(current_user: User = Depends(get_current_user)):
    """Check if current user has admin role"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
