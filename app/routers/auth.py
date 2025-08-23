from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPAuthorizationCredentials
from ..auth import (
    AuthService,
    UserRegisterRequest,
    UserLoginRequest,
    UserResponse,
    Token,
    PasswordResetRequest,
    PasswordUpdateRequest,
    security,
)
from ..models.user import User
from ..services.email_service import EmailService
from ..services.otp_service import OTPService
from typing import Dict, Any

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


# Dependency to get current user
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """Dependency to get current authenticated user"""
    return await AuthService.get_current_user(credentials.credentials)


@router.post(
    "/register",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Register a new student account with email, password, and basic information",
)
async def register(user_data: UserRegisterRequest):
    """
    Register a new user account.

    - **name**: Full name of the user
    - **email**: Valid email address (will be used for login)
    - **phone**: Phone number (Indian format)
    - **password**: Strong password (min 8 chars, uppercase, lowercase, number, special char)
    - **preferred_exam_categories**: List of exam categories user is interested in

    Returns user information and success message.
    """
    try:
        new_user = await AuthService.register_user(user_data)
        user_response = AuthService.convert_user_to_response(new_user)

        return {
            "message": "User registered successfully",
            "user": user_response,
            "next_steps": [
                "Please verify your email address",
                "Complete your profile setup",
                "Explore available courses and mock tests",
            ],
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}",
        )


@router.post(
    "/login",
    response_model=Dict[str, Any],
    summary="Login user",
    description="Authenticate user and return access tokens",
)
async def login(login_data: UserLoginRequest):
    """
    Login with email and password.

    - **email**: Registered email address
    - **password**: User password

    Returns access token, refresh token, and user information.
    """
    try:
        user, token = await AuthService.login_user(login_data)
        user_response = AuthService.convert_user_to_response(user)

        return {
            "message": "Login successful",
            "user": user_response,
            "tokens": token,
            "dashboard_url": f"/dashboard/{user.role.value}",
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}",
        )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    description="Get the profile information of the currently authenticated user",
)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user's profile information.

    Requires valid access token in Authorization header.
    """
    return AuthService.convert_user_to_response(current_user)


@router.post(
    "/refresh",
    response_model=Token,
    summary="Refresh access token",
    description="Get a new access token using refresh token",
)
async def refresh_access_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Refresh access token using refresh token.

    Send refresh token in Authorization header to get new access token.
    """
    import jwt
    from ..auth import SECRET_KEY, ALGORITHM

    try:
        # Verify refresh token
        payload = jwt.decode(
            credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM]
        )
        email: str = payload.get("sub")
        token_type: str = payload.get("type")

        if email is None or token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if user exists and is active
        user = await User.find_one({"email": email})
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        # Create new tokens
        access_token = AuthService.create_access_token(data={"sub": user.email})
        refresh_token = AuthService.create_refresh_token(data={"sub": user.email})

        return Token(
            access_token=access_token, refresh_token=refresh_token, token_type="bearer"
        )

    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token refresh failed: {str(e)}",
        )


@router.post(
    "/send-verification-email",
    response_model=Dict[str, str],
    summary="Send verification email",
    description="Send OTP verification email to user's email address",
)
async def send_verification_email(
    request_data: dict,
    current_user: User = Depends(get_current_user),
):
    """Send verification email with OTP"""
    try:
        email = request_data.get("email")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Email is required"
            )

        # Generate OTP
        otp = OTPService.generate_otp()
        expiry = OTPService.generate_otp_expiry()

        # Update user with OTP
        current_user.email_verification_otp = otp
        current_user.email_verification_otp_expires_at = expiry
        await current_user.save()

        # Send email
        success = await EmailService.send_verification_email(email, otp)

        if success:
            return {
                "message": "Verification email sent successfully",
                "note": "Check your email for the OTP code",
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send verification email",
            )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send verification email: {str(e)}",
        )


@router.post(
    "/verify-email",
    response_model=Dict[str, str],
    summary="Verify email with OTP",
    description="Verify email address using OTP code",
)
async def verify_email(
    request_data: dict,  # {"email": "user@example.com", "otp": "123456"}
    current_user: User = Depends(get_current_user),
):
    """Verify email with OTP"""
    try:
        email = request_data.get("email")
        otp = request_data.get("otp")

        if not email or not otp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email and OTP are required",
            )

        # Check if OTP matches and is not expired
        if (
            current_user.email_verification_otp == otp
            and not OTPService.is_otp_expired(
                current_user.email_verification_otp_expires_at
            )
        ):

            # Mark email as verified and clear OTP
            current_user.is_email_verified = True
            current_user.email_verification_otp = None
            current_user.email_verification_otp_expires_at = None
            await current_user.save()

            return {
                "message": "Email verified successfully",
                "user": AuthService.convert_user_to_response(current_user),
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OTP"
            )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Email verification failed: {str(e)}",
        )


@router.put(
    "/profile",
    response_model=UserResponse,
    summary="Update user profile",
    description="Update current user's profile information",
)
async def update_profile(
    update_data: dict, current_user: User = Depends(get_current_user)
):
    """
    Update user profile information.

    Allowed fields: name, phone, preferred_exam_categories
    """
    try:
        allowed_fields = {"name", "phone", "preferred_exam_categories"}
        update_fields = {k: v for k, v in update_data.items() if k in allowed_fields}

        if not update_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid fields provided for update",
            )

        # Validate phone if provided
        if "phone" in update_fields:
            if not AuthService.validate_phone(update_fields["phone"]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid phone number format",
                )

            # Check if phone already exists for another user
            existing_phone = await User.find_one(
                {"phone": update_fields["phone"], "_id": {"$ne": current_user.id}}
            )
            if existing_phone:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Phone number already exists",
                )

        # Update user
        for field, value in update_fields.items():
            setattr(current_user, field, value)

        current_user.update_timestamp()
        await current_user.save()

        return AuthService.convert_user_to_response(current_user)

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Profile update failed: {str(e)}",
        )


@router.post(
    "/change-password",
    response_model=Dict[str, str],
    summary="Change password",
    description="Change user password",
)
async def change_password(
    password_data: PasswordUpdateRequest, current_user: User = Depends(get_current_user)
):
    """
    Change user password.

    - **current_password**: Current password for verification
    - **new_password**: New password (must meet strength requirements)
    """
    try:
        # Verify current password
        if not AuthService.verify_password(
            password_data.current_password, current_user.password_hash
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )

        # Validate new password
        if not AuthService.validate_password(password_data.new_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be at least 8 characters long and contain uppercase, lowercase, number, and special character",
            )

        # Update password
        current_user.password_hash = AuthService.get_password_hash(
            password_data.new_password
        )
        current_user.update_timestamp()
        await current_user.save()

        return {"message": "Password updated successfully"}

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Password change failed: {str(e)}",
        )


@router.post(
    "/logout",
    response_model=Dict[str, str],
    summary="Logout user",
    description="Logout current user (client-side token removal)",
)
async def logout(current_user: User = Depends(get_current_user)):
    """
    Logout user.

    Note: This is mainly for client-side token removal.
    JWT tokens remain valid until expiry.
    """
    return {
        "message": "Logged out successfully",
        "instruction": "Please remove tokens from client storage",
    }


@router.post(
    "/forgot-password",
    response_model=Dict[str, str],
    summary="Request password reset",
    description="Request password reset link (placeholder implementation)",
)
async def forgot_password(request_data: PasswordResetRequest):
    """
    Request password reset.

    Note: This is a placeholder implementation.
    In production, this would send a reset email.
    """
    # Check if user exists
    user = await User.find_one({"email": request_data.email})

    # Always return success message for security (don't reveal if email exists)
    return {
        "message": "If the email exists, a password reset link will be sent",
        "note": "This is a placeholder implementation. Email functionality not yet implemented.",
    }


@router.get(
    "/verify-token",
    response_model=Dict[str, Any],
    summary="Verify token validity",
    description="Check if the provided token is valid",
)
async def verify_token(current_user: User = Depends(get_current_user)):
    """
    Verify if the provided token is valid and return user info.
    """
    return {
        "valid": True,
        "user": AuthService.convert_user_to_response(current_user),
        "message": "Token is valid",
    }
