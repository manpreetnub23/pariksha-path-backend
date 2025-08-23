import secrets
import string
from datetime import datetime, timedelta, timezone


class OTPService:
    @staticmethod
    def generate_otp(length: int = 6) -> str:
        """Generate a random numeric OTP"""
        return "".join(secrets.choice(string.digits) for _ in range(length))

    @staticmethod
    def generate_otp_expiry(minutes: int = 10) -> datetime:
        """Generate OTP expiry timestamp"""
        return datetime.now(timezone.utc) + timedelta(minutes=minutes)

    @staticmethod
    def is_otp_expired(expiry_timestamp: datetime) -> bool:
        """Check if OTP has expired"""
        return datetime.now(timezone.utc) > expiry_timestamp
