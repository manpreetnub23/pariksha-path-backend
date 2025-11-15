from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks, Request
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
from ..models.user_session import UserSession
from ..services.email_service import EmailService
from ..services.otp_service import OTPService
from ..services.session_service import SessionService
from ..dependencies import get_current_user, security, ensure_db
from typing import Dict, Any
from datetime import datetime, timezone
from ..input_sanitizer import sanitizer
import logging
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Register a new student account with email, password, and basic information",
)
async def register(user_data: UserRegisterRequest, background_tasks: BackgroundTasks):
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
        # Sanitize user input
        sanitized_data = sanitizer.sanitize_dict(user_data.dict())

        # Do not use background_tasks for OTP email
        new_user = await AuthService.register_user(
            UserRegisterRequest(**sanitized_data),
            None
        )

        user_response = AuthService.convert_user_to_response(new_user)
        # Generate and send verification OTP synchronously
        await AuthService.generate_and_send_otp(new_user.email, background_tasks=None, sync_send=True)

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
async def login(
    request_data: UserLoginRequest,
    background_tasks: BackgroundTasks,
    request: Request = None,
):
    """
    Authenticate user and either return tokens or request OTP verification.

    If OTP verification is enabled, an OTP will be sent to the user's email,
    and the user will need to verify it before receiving tokens.

    Otherwise, returns access token, refresh token, and user information directly.
    """
    try:

        # Sanitize login input
        sanitized_data = sanitizer.sanitize_dict(request_data.dict())
        login_data = UserLoginRequest(**sanitized_data)

        user = await AuthService.authenticate_user(
            login_data.email, login_data.password
        )

        if not user:
            logger.exception("Unexpected error during login")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            logger.exception("Unexpected error during login")
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

            # Send OTP email synchronously (never use background_tasks)
            logger.info(f"📧 Sending login OTP to {user.email}...")
            email_sent = await EmailService.send_login_otp_email(user.email, otp)
            if email_sent:
                logger.info(f"✅ Login OTP email sent to {user.email}")
            else:
                logger.error(f"❌ Failed to send login OTP email to {user.email}")

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
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

        # Create session for the new refresh token
        try:
            # Extract device info from request (if available)
            user_agent = None
            ip_address = None
            if request:
                user_agent = request.headers.get("user-agent")
                ip_address = request.client.host if request.client else None

            await SessionService.create_session(
                user_id=str(user.id),
                refresh_token=token.refresh_token,
                user_agent=user_agent,
                ip_address=ip_address,
            )
        except Exception as e:
            logger.warning(f"Failed to create session for user {user.email}: {str(e)}")
            # Continue with login even if session creation fails

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
        logger.exception(f"Login error: {str(e)}")
        # Log more details about the exception to help diagnose connection issues
        print(f"Login error details - Type: {type(e).__name__}, Message: {str(e)}")

        # More specific error message based on the exception type
        if "ConnectionFailure" in str(
            type(e).__name__
        ) or "ServerSelectionTimeoutError" in str(type(e).__name__):
            detail = (
                "Database connection error. Please try again later or contact support."
            )
        else:
            detail = f"Login failed: {str(e)}"

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
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
    description="Get a new access token using refresh token with proper session management",
)
async def refresh_access_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    request: Request = None,
):
    """
    Refresh access token using refresh token with session management.

    This endpoint now:
    1. Validates the refresh token against active sessions
    2. Creates new token pair with rotation
    3. Blacklists the old refresh token
    4. Creates new session record
    """
    import jwt
    from ..auth import SECRET_KEY, ALGORITHM

    try:
        # Extract device information from request
        user_agent = None
        ip_address = None
        if request:
            user_agent = request.headers.get("user-agent")
            ip_address = request.client.host if request.client else None

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

        # Validate session and check for blacklisting
        session = await SessionService.validate_session(credentials.credentials)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired or invalid",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check for suspicious activity
        if session.suspicious_activity:
            logger.warning(f"Suspicious session refresh attempt for user {email}")
            # Still allow refresh but log the activity
            session.add_activity_log(
                "suspicious_refresh", "Refresh attempt on suspicious session"
            )

        # Blacklist the old refresh token by deactivating the session
        await SessionService.blacklist_refresh_token(credentials.credentials)

        # Create new tokens
        access_token = AuthService.create_access_token(data={"sub": user.email})
        refresh_token = AuthService.create_refresh_token(data={"sub": user.email})

        # Create new session for the new refresh token
        new_session = await SessionService.create_session(
            user_id=str(user.id),
            refresh_token=refresh_token,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        logger.info(
            f"✅ Token refreshed successfully for user {email}, new session: {new_session.id}"
        )

        return Token(
            access_token=access_token, refresh_token=refresh_token, token_type="bearer"
        )

    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed for user {email}: {str(e)}")
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
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    """Send verification email with OTP"""
    try:
        email = request_data.get("email")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Email is required"
            )

        # Always send OTP synchronously (never use background_tasks)
        success = await AuthService.generate_and_send_otp(email, background_tasks=None, sync_send=True)
        if success:
            return {
                "message": "Verification email sent successfully",
                "note": "Check your email for the OTP code",
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
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
    request: Request = None,
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
                expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            )

            # Create session for the new refresh token
            try:
                # Extract device info from request (if available)
                user_agent = None
                ip_address = None
                if request:
                    user_agent = request.headers.get("user-agent")
                    ip_address = request.client.host if request.client else None

                await SessionService.create_session(
                    user_id=str(user.id),
                    refresh_token=token.refresh_token,
                    user_agent=user_agent,
                    ip_address=ip_address,
                )
            except Exception as e:
                logger.warning(
                    f"Failed to create session for user {user.email}: {str(e)}"
                )
                # Continue with login even if session creation fails

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
    summary="Verify email with OTP (for logged-in users)",
    description="Verify email address using OTP code for logged-in users",
)
async def verify_email(
    request_data: dict,  # {"email": "user@example.com", "otp": "123456"}
    current_user: User = Depends(get_current_user),
):
    """Verify email with OTP for logged-in users"""
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


@router.post(
    "/verify-registration",
    response_model=Dict[str, Any],
    summary="Verify email after registration",
    description="Verify email address using OTP code after registration (no login required)",
)
async def verify_registration_email(
    request_data: dict,  # {"email": "user@example.com", "otp": "123456"}
    request: Request = None,
):
    """
    Verify email with OTP after registration without requiring login.

    This endpoint allows users to verify their email immediately after registration
    before logging in for the first time.

    Args:
        request_data: Dictionary containing email and OTP

    Returns:
        Success message and user data on successful verification
    """
    try:
        email = request_data.get("email")
        otp = request_data.get("otp")

        if not email or not otp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email and OTP are required",
            )

        # Use the AuthService to verify the OTP
        success = await AuthService.verify_email_otp(email, otp)

        if success:
            # Get the updated user to return in response
            user = await User.find_one({"email": email})
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found",
                )

            # Generate tokens to allow immediate login after verification
            token = Token(
                access_token=AuthService.create_access_token(data={"sub": user.email}),
                refresh_token=AuthService.create_refresh_token(
                    data={"sub": user.email}
                ),
                token_type="bearer",
                expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            )

            # Create session for the new refresh token
            try:
                # Extract device info from request (if available)
                user_agent = None
                ip_address = None
                if request:
                    user_agent = request.headers.get("user-agent")
                    ip_address = request.client.host if request.client else None

                await SessionService.create_session(
                    user_id=str(user.id),
                    refresh_token=token.refresh_token,
                    user_agent=user_agent,
                    ip_address=ip_address,
                )
            except Exception as e:
                logger.warning(
                    f"Failed to create session for user {user.email}: {str(e)}"
                )
                # Continue with verification even if session creation fails

            return {
                "message": "Email verified successfully",
                "user": AuthService.convert_user_to_response(user),
                "tokens": token,
                "dashboard_url": f"/dashboard/{user.role.value}",
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


# manpreet ne add kiya hai
# ------------------------------ yahan se


@router.post(
    "/resend-verification-email",
    response_model=Dict[str, str],
    summary="Resend OTP for email verification",
)
async def resend_verification_email(
    request_data: dict,
    background_tasks: BackgroundTasks,
):
    """
    Resend OTP to user's email for verification.
    """
    try:
        email = request_data.get("email")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Email is required"
            )

        # Always send OTP synchronously (never use background_tasks)
        success = await AuthService.generate_and_send_otp(email, background_tasks=None, sync_send=True)
        if success:
            return {
                "message": "Verification email resent successfully",
                "note": "Check your email for the OTP code",
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resend verification email: {str(e)}",
        )


# -------------------------------------------------- yahan tak


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
        # Sanitize update data
        sanitized_data = sanitizer.sanitize_dict(update_data)
        allowed_fields = {"name", "phone", "preferred_exam_categories"}
        update_fields = {k: v for k, v in sanitized_data.items() if k in allowed_fields}

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
    summary="Logout user with session invalidation",
    description="Logout current user and invalidate all active sessions",
)
async def logout(current_user: User = Depends(get_current_user)):
    """
    Enhanced logout with proper session management:

    1. Invalidates all active sessions for the user
    2. Blacklists all refresh tokens
    3. Logs the logout activity
    4. Returns confirmation
    """
    try:
        user_id = str(current_user.id)

        # Invalidate all user sessions
        invalidated_count = await SessionService.invalidate_all_user_sessions(user_id)

        logger.info(
            f"🚪 User {current_user.email} logged out, invalidated {invalidated_count} sessions"
        )

        return {
            "message": "Logged out successfully",
            "detail": f"Invalidated {invalidated_count} active sessions",
            "sessions_invalidated": invalidated_count,
            "instruction": "All tokens are now invalid across all devices",
        }

    except Exception as e:
        logger.error(f"Logout failed for user {current_user.email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout failed: {str(e)}",
        )


@router.post(
    "/forgot-password",
    response_model=Dict[str, str],
    summary="Request password reset",
    description="Request password reset OTP via email",
)
async def forgot_password(
    request_data: PasswordResetRequest,
    background_tasks: BackgroundTasks,
):
    """
    Request a password reset by sending an OTP to the user's registered email.

    - **email**: Email address of the account to reset password for
    """
    try:
        user = await User.find_one({"email": request_data.email})

        if user:
            # Generate OTP
            otp = OTPService.generate_otp()
            expiry = OTPService.generate_otp_expiry()

            # Update user with reset password OTP
            user.reset_password_otp = otp
            user.reset_password_otp_expires_at = expiry
            await user.save()

            # ✅ Send email SYNCHRONOUSLY (await) - Don't rely on BackgroundTasks
            logger.info(f"📧 Sending password reset OTP to {request_data.email}...")
            email_sent = await EmailService.send_password_reset_email(request_data.email, otp)
            if email_sent:
                logger.info(f"✅ Password reset email sent to {request_data.email}")
            else:
                logger.error(f"❌ Failed to send password reset email to {request_data.email}")

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
    "/sessions",
    response_model=Dict[str, Any],
    summary="Get user sessions",
    description="Get all active sessions for the current user",
)
async def get_user_sessions(current_user: User = Depends(get_current_user)):
    """
    Get all active sessions for the current user.

    Returns session information including device details and activity.
    """
    try:
        sessions = await SessionService.get_user_sessions(str(current_user.id))
        session_data = [session.to_dict() for session in sessions]

        return {
            "message": "Sessions retrieved successfully",
            "sessions": session_data,
            "total_active": len(session_data),
        }

    except Exception as e:
        logger.error(
            f"Failed to retrieve sessions for user {current_user.email}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve sessions: {str(e)}",
        )


@router.post(
    "/sessions/{session_id}/invalidate",
    response_model=Dict[str, str],
    summary="Invalidate specific session",
    description="Invalidate a specific session by ID",
)
async def invalidate_session(
    session_id: str, current_user: User = Depends(get_current_user)
):
    """
    Invalidate a specific session for the current user.

    This will blacklist the refresh token for that session.
    """
    try:
        # Find the session
        session = await UserSession.get(session_id)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
            )

        # Verify ownership
        if session.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only invalidate your own sessions",
            )

        # Invalidate the session
        session.deactivate()
        await session.save()

        logger.info(f"🔒 Session {session_id} invalidated by user {current_user.email}")

        return {
            "message": "Session invalidated successfully",
            "session_id": session_id,
            "detail": "Refresh token for this session is now blacklisted",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to invalidate session {session_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to invalidate session: {str(e)}",
        )


@router.post(
    "/logout-all",
    response_model=Dict[str, str],
    summary="Logout from all devices",
    description="Invalidate all sessions across all devices for the current user",
)
async def logout_all_devices(current_user: User = Depends(get_current_user)):
    """
    Force logout from all devices by invalidating all sessions.

    This is useful for security purposes or when user wants to ensure
    no other sessions remain active.
    """
    try:
        user_id = str(current_user.id)
        invalidated_count = await SessionService.invalidate_all_user_sessions(user_id)

        logger.info(
            f"🚪🔥 All sessions invalidated for user {current_user.email} ({invalidated_count} sessions)"
        )

        return {
            "message": "Logged out from all devices successfully",
            "detail": f"Invalidated {invalidated_count} sessions across all devices",
            "sessions_invalidated": invalidated_count,
            "instruction": "All tokens are now invalid across all devices and browsers",
        }

    except Exception as e:
        logger.error(
            f"Failed to logout all devices for user {current_user.email}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to logout all devices: {str(e)}",
        )
