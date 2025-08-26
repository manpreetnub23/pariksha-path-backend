from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPAuthorizationCredentials
from ..auth import (
    AuthService,
    UserRegisterRequest,
    UserLoginRequest,
    UserResponse,
    Token,
    LoginResponse,
    PasswordResetRequest,
    PasswordUpdateRequest,
    ResetPasswordWithOTPRequest,
)
from ..models.user import User
from ..services.email_service import EmailService
from ..services.otp_service import OTPService
from typing import Dict, Any
from datetime import datetime, timezone
from ..auth import ACCESS_TOKEN_EXPIRE_MINUTES
from ..dependencies import get_current_user, security

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


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

        # Send welcome email
        await EmailService.send_welcome_email(new_user.email, new_user.name)

        # Generate and send verification OTP
        otp = OTPService.generate_otp()
        expiry = OTPService.generate_otp_expiry()
        new_user.email_verification_otp = otp
        new_user.email_verification_otp_expires_at = expiry
        await new_user.save()

        await EmailService.send_verification_email(new_user.email, otp)

        return {
            "message": "User registered successfully",
            "user": user_response,
            "next_steps": [
                "Please verify your email address with the OTP sent",
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
    response_model=LoginResponse,
    summary="Login user",
    description="Authenticate user and either return tokens or request OTP verification",
)
async def login(login_data: UserLoginRequest):
    """
    Login with email and password.

    - **email**: Registered email address
    - **password**: User password

    If OTP verification is enabled, an OTP will be sent to the user's email,
    and the user will need to verify it before receiving tokens.

    Otherwise, returns access token, refresh token, and user information directly.
    """
    try:
        from ..config import settings

        user = await AuthService.authenticate_user(
            login_data.email, login_data.password
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account is deactivated. Please contact admin.",
            )

        # Update last login
        user.last_login = datetime.now(timezone.utc)
        user.update_timestamp()
        await user.save()

        # Check if login OTP verification is required
        if settings.LOGIN_OTP_REQUIRED:
            # Generate OTP
            otp = OTPService.generate_otp()
            expiry = OTPService.generate_otp_expiry()

            # Update user with login OTP
            user.login_otp = otp
            user.login_otp_expires_at = expiry
            await user.save()

            # Send OTP email
            success = await EmailService.send_login_otp_email(user.email, otp)
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to send verification email",
                )

            # Return response indicating OTP verification is required
            return LoginResponse(
                message="Login requires verification",
                requires_verification=True,
                user=AuthService.convert_user_to_response(user).dict(),
            )

        # If OTP is not required, return tokens directly
        token = Token(
            access_token=AuthService.create_access_token(data={"sub": user.email}),
            refresh_token=AuthService.create_refresh_token(data={"sub": user.email}),
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

        return LoginResponse(
            message="Login successful",
            requires_verification=False,
            user=AuthService.convert_user_to_response(user).dict(),
            tokens=token,
            dashboard_url=f"/dashboard/{user.role.value}",
        )

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

    Send refresh token in Authorization header to get new access token hehe.
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
    "/verify-login",
    response_model=Dict[str, Any],
    summary="Verify login with OTP",
    description="Complete login by verifying OTP sent to email",
)
async def verify_login(
    request_data: dict,
):  # {"email": "user@example.com", "otp": "123456"}
    """
    Verify login with OTP.

    After login, if OTP verification is required, this endpoint is used to verify
    the OTP and complete the login process.

    Returns access token, refresh token, and user information.
    """
    try:
        email = request_data.get("email")
        otp = request_data.get("otp")

        if not email or not otp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email and OTP are required",
            )

        # Find user by email
        user = await User.find_one({"email": email})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User not found",
            )

        # Check if OTP matches and is not expired
        if user.login_otp == otp and not OTPService.is_otp_expired(
            user.login_otp_expires_at
        ):
            # Clear OTP
            user.login_otp = None
            user.login_otp_expires_at = None
            await user.save()

            # Generate tokens
            token = Token(
                access_token=AuthService.create_access_token(data={"sub": user.email}),
                refresh_token=AuthService.create_refresh_token(
                    data={"sub": user.email}
                ),
                token_type="bearer",
                expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            )

            return {
                "message": "Login verification successful",
                "user": AuthService.convert_user_to_response(user),
                "tokens": token,
                "dashboard_url": f"/dashboard/{user.role.value}",
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OTP",
            )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login verification failed: {str(e)}",
        )


@router.post(
    "/verify-email",
    response_model=Dict[str, Any],
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
    description="Request password reset OTP via email",
)
async def forgot_password(request_data: PasswordResetRequest):
    """
    Request a password reset by sending an OTP to the user's registered email.

    - **email**: Email address of the account to reset password for
    """
    try:
        # Check if user exists but don't reveal this information in the response
        user = await User.find_one({"email": request_data.email})

        if user:
            # Generate OTP
            otp = OTPService.generate_otp()
            expiry = OTPService.generate_otp_expiry()

            # Update user with reset password OTP
            user.reset_password_otp = otp
            user.reset_password_otp_expires_at = expiry
            await user.save()

            # Send email with OTP
            await EmailService.send_password_reset_email(request_data.email, otp)

        # Always return success message for security (don't reveal if email exists)
        return {
            "message": "If the email exists, a password reset code has been sent",
            "detail": "Please check your email for the reset code",
        }

    except Exception as e:
        # Log the error but don't reveal specifics in the response
        print(f"Password reset request failed: {str(e)}")
        return {
            "message": "If the email exists, a password reset code has been sent",
            "detail": "Please check your email for the reset code",
        }


@router.post(
    "/reset-password",
    response_model=Dict[str, str],
    summary="Reset password with OTP",
    description="Reset password using OTP sent to email",
)
async def reset_password_with_otp(reset_data: ResetPasswordWithOTPRequest):
    """
    Reset password using OTP sent to email.

    - **email**: Email address of the account
    - **otp**: The OTP code received via email
    - **new_password**: New password to set
    """
    try:
        # Find user by email
        user = await User.find_one({"email": reset_data.email})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset code",
            )

        # Check if OTP matches and is not expired
        if user.reset_password_otp == reset_data.otp and not OTPService.is_otp_expired(
            user.reset_password_otp_expires_at
        ):

            # Validate new password
            if not AuthService.validate_password(reset_data.new_password):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Password must be at least 8 characters long and contain uppercase, lowercase, number, and special character",
                )

            # Update password and clear OTP
            user.password_hash = AuthService.get_password_hash(reset_data.new_password)
            user.reset_password_otp = None
            user.reset_password_otp_expires_at = None
            user.update_timestamp()
            await user.save()

            return {
                "message": "Password reset successful",
                "detail": "You can now log in with your new password",
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset code",
            )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Password reset failed: {str(e)}",
        )


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
