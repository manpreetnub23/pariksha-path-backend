from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import HTTPException, status, BackgroundTasks
from fastapi.security import HTTPBearer
import jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from .models.user import User
from .models.enums import UserRole, ExamCategory
from .config import settings
from typing import Dict, Any
import os
import logging

# import secrets
from .services.otp_service import OTPService
from .services.email_service import EmailService
from .db import init_beanie_if_needed  # Import the new function

import re

# Configure logging
logger = logging.getLogger(__name__)

security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS


class TokenData(BaseModel):
    email: Optional[str] = None


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = ACCESS_TOKEN_EXPIRE_MINUTES * 60


class UserRegisterRequest(BaseModel):
    name: str
    email: EmailStr
    phone: str
    password: str
    preferred_exam_categories: list[ExamCategory] = []

    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe",
                "email": "john@example.com",
                "phone": "+911234567890",
                "password": "SecurePassword123!",
                "preferred_exam_categories": ["medical", "engineering"],
            }
        }


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

    class Config:
        json_schema_extra = {
            "example": {"email": "john@example.com", "password": "SecurePassword123!"}
        }


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    role: UserRole
    is_active: bool
    is_verified: bool
    enrolled_courses: list[str]
    preferred_exam_categories: list[ExamCategory]
    purchased_test_series: list[str]
    has_premium_access: bool
    created_at: datetime
    last_login: Optional[datetime] = None


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordUpdateRequest(BaseModel):
    current_password: str
    new_password: str


class ResetPasswordWithOTPRequest(BaseModel):
    email: EmailStr
    otp: str
    new_password: str


class LoginResponse(BaseModel):
    message: str
    requires_verification: bool
    user: Dict[str, Any]
    tokens: Optional[Token] = None
    dashboard_url: Optional[str] = None


class AuthService:
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)

    @staticmethod
    def validate_password(password: str) -> bool:
        """
        Validate password strength:
        - At least 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one number
        - At least one special character
        """
        if len(password) < 8:
            return False

        if not re.search(r"[A-Z]", password):
            return False

        if not re.search(r"[a-z]", password):
            return False

        if not re.search(r"\d", password):
            return False

        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            return False

        return True

    @staticmethod
    def validate_phone(phone: str) -> bool:
        """Validate phone number format"""
        # Indian phone number validation (10 digits, optional +91)
        pattern = r"^(\+91)?[6-9]\d{9}$"
        return bool(re.match(pattern, phone))

    @staticmethod
    def create_access_token(
        data: dict, expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=ACCESS_TOKEN_EXPIRE_MINUTES
            )

        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    @staticmethod
    def create_refresh_token(data: dict) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    @staticmethod
    async def authenticate_user(email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password"""
        try:
            # Ensure database is initialized BEFORE any database operation
            await init_beanie_if_needed()

            user = await User.find_one({"email": email})

            if not user:
                return None

            password_valid = AuthService.verify_password(password, user.password_hash)

            if not password_valid:
                return None

            return user
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            # Re-raise to be handled by the caller
            raise

    @staticmethod
    async def verify_token(token: str) -> TokenData:
        """Verify JWT token and return token data"""
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            email: str = payload.get("sub")
            token_type: str = payload.get("type")

            if email is None or token_type != "access":
                raise credentials_exception

            token_data = TokenData(email=email)
        except jwt.PyJWTError:
            raise credentials_exception

        return token_data

    @staticmethod
    async def generate_and_send_otp(
        email: str, 
        background_tasks: Optional[BackgroundTasks] = None,
        sync_send: bool = True  # NEW: Force synchronous sending for critical flows
    ) -> bool:
        """Generate OTP and send verification email"""
        # Ensure database is initialized
        await init_beanie_if_needed()

        user = await User.find_one({"email": email})
        if not user:
            logger.warning(f"User not found for OTP generation: {email}")
            return False

        # Generate OTP
        otp = OTPService.generate_otp()
        expiry = OTPService.generate_otp_expiry()
        logger.info(f"📧 Generated OTP for {email}: {otp}")

        # Update user with OTP (fast DB operation)
        user.email_verification_otp = otp
        user.email_verification_otp_expires_at = expiry
        await user.save()
        logger.info(f"✅ OTP stored in database for {email}")

        # ✅ SEND EMAIL SYNCHRONOUSLY (await) - Don't rely on BackgroundTasks
        # This ensures email is sent before response is returned
        logger.info(f"📨 Sending OTP email to {email} (synchronously)...")
        result = await EmailService.send_verification_email(email, otp)
        
        if result:
            logger.info(f"✅ OTP email sent successfully to {email}")
        else:
            logger.error(f"❌ Failed to send OTP email to {email}")
        
        return result

    @staticmethod
    async def verify_email_otp(email: str, otp: str) -> bool:
        """Verify email OTP"""
        # Ensure database is initialized
        await init_beanie_if_needed()

        user = await User.find_one({"email": email})
        if not user:
            return False

        # Check if OTP exists
        if not user.email_verification_otp:
            return False

        # Check if OTP expired (using proper method that handles timezone issues)
        if OTPService.is_otp_expired(user.email_verification_otp_expires_at):
            return False

        # Check if OTP matches
        if user.email_verification_otp != otp:
            return False

        # Mark email as verified and clear OTP
        user.is_verified = True
        user.email_verification_otp = None
        user.email_verification_otp_expires_at = None
        await user.save()
        return True

    @staticmethod
    async def get_current_user(token: str) -> User:
        """Get current user from JWT token"""
        # Ensure database is initialized
        await init_beanie_if_needed()

        token_data = await AuthService.verify_token(token)
        user = await User.find_one({"email": token_data.email})

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
            )

        return user

    @staticmethod
    async def register_user(
        user_data: UserRegisterRequest,
        background_tasks: Optional[BackgroundTasks] = None
    ) -> User:
        """Register a new user"""
        # Ensure database is initialized
        await init_beanie_if_needed()

        # Check if user already exists
        existing_user = await User.find_one({"email": user_data.email})
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists",
            )

        # Check phone number
        existing_phone = await User.find_one({"phone": user_data.phone})
        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this phone number already exists",
            )

        # Validate password strength
        if not AuthService.validate_password(user_data.password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters long and contain uppercase, lowercase, number, and special character",
            )

        # Validate phone number
        if not AuthService.validate_phone(user_data.phone):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid phone number format",
            )

        # Hash password
        hashed_password = AuthService.get_password_hash(user_data.password)

        # Create new user
        new_user = User(
            name=user_data.name,
            email=user_data.email,
            phone=user_data.phone,
            password_hash=hashed_password,
            preferred_exam_categories=user_data.preferred_exam_categories,
            role=UserRole.STUDENT,
            is_active=True,
            is_verified=False,  # User needs to verify email
        )

        await new_user.insert()

        # Send welcome email (don't wait for it - use background tasks)
        if background_tasks:
            background_tasks.add_task(
                EmailService.send_welcome_email, new_user.email, new_user.name
            )

        return new_user

    @staticmethod
    async def login_user(
        login_data: UserLoginRequest,
        background_tasks: Optional[BackgroundTasks] = None
    ) -> tuple[User, Token]:
        """Login user and return tokens"""
        # Ensure database is initialized
        await init_beanie_if_needed()

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

        # ✅ Update last login in background (non-blocking)
        if background_tasks:
            background_tasks.add_task(
                AuthService._update_last_login, user.email
            )
        else:
            # Fallback: update synchronously if no background_tasks
            user.last_login = datetime.now(timezone.utc)
            user.update_timestamp()
            await user.save()

        # Create tokens
        access_token = AuthService.create_access_token(data={"sub": user.email})
        refresh_token = AuthService.create_refresh_token(data={"sub": user.email})

        token = Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

        return user, token

    @staticmethod
    async def _update_last_login(email: str) -> None:
        """Helper to update last login timestamp in background"""
        try:
            await init_beanie_if_needed()
            user = await User.find_one({"email": email})
            if user:
                user.last_login = datetime.now(timezone.utc)
                user.update_timestamp()
                await user.save()
        except Exception as e:
            logger.warning(f"Failed to update last login for {email}: {str(e)}")

    @staticmethod
    def convert_user_to_response(user: User) -> UserResponse:
        """Convert User model to UserResponse"""
        return UserResponse(
            id=str(user.id),
            name=user.name,
            email=user.email,
            phone=user.phone,
            role=user.role,
            is_active=user.is_active,
            is_verified=user.is_verified,
            enrolled_courses=user.enrolled_courses,
            preferred_exam_categories=user.preferred_exam_categories,
            purchased_test_series=user.purchased_test_series,
            has_premium_access=user.has_premium_access,
            created_at=user.created_at,
            last_login=user.last_login,
        )
