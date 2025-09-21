"""
Admin account management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any

from ...models.user import User
from ...models.enums import UserRole
from ...dependencies import admin_required
from ...services.admin_service import AdminService
from ...auth import AuthService, UserRegisterRequest
from ...models.admin_action import ActionType

router = APIRouter(prefix="/admin", tags=["Admin - Management"])


@router.post(
    "/create-admin",
    response_model=Dict[str, Any],
    summary="Create admin account",
    description="Admin endpoint to create another admin account",
)
async def create_admin(
    admin_data: UserRegisterRequest,
    current_user: User = Depends(admin_required),
):
    """Create a new admin account (Admin only)"""
    try:
        # Create admin user
        hashed_password = AuthService.get_password_hash(admin_data.password)
        new_admin = User(
            name=admin_data.name,
            email=admin_data.email,
            phone=admin_data.phone,
            password_hash=hashed_password,
            role=UserRole.ADMIN,  # Set role as ADMIN
            is_active=True,
            is_verified=True,  # Auto-verify admin accounts
        )
        await new_admin.insert()

        # Log the admin creation
        await AdminService.log_admin_action(
            str(current_user.id),
            ActionType.CREATE,
            "users",
            str(new_admin.id),
            {"action": "admin_created"},
        )

        return AdminService.format_response(
            "Admin created successfully",
            data={"admin_id": str(new_admin.id)},
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create admin: {str(e)}",
        )
