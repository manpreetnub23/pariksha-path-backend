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
    def is_otp_expired(expiry_time: datetime) -> bool:
        """
        Check if OTP has expired, handling both timezone-aware and timezone-naive datetimes.

        Args:
            expiry_time: The expiry datetime to check

        Returns:
            bool: True if OTP has expired, False otherwise
        """
        now = datetime.now(timezone.utc)
        if expiry_time.tzinfo is None:
            expiry_time = expiry_time.replace(tzinfo=timezone.utc)
        return now > expiry_time
