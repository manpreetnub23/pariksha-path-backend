import logging
from pydantic_settings import BaseSettings

# Set up logging for this module
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    # Database
    MONGO_URI: str

    # JWT Authentication
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int

    # Email configuration - Updated for Resend
    SMTP_SERVER: str = "smtp.resend.com"
    SMTP_PORT: int = 587  # Use 587 for STARTTLS (Resend recommended)
    SENDER_EMAIL: str | None = None  # This will be your verified domain email
    SENDER_PASSWORD: str | None = None  # This will be your Resend API key

    # Security settings
    LOGIN_OTP_REQUIRED: bool = (
        True  # Require OTP verification during login (set to True in production)
    )

    # DigitalOcean Spaces configuration
    DO_SPACES_ENDPOINT: str
    DO_SPACES_KEY: str
    DO_SPACES_SECRET: str
    DO_SPACES_BUCKET: str
    DO_SPACES_REGION: str = "nyc3"  # Change to your region
    DO_SPACES_CDN_ENDPOINT: str  # Optional: CDN endpoint for faster access
    
    RAZORPAY_KEY_ID: str
    RAZORPAY_KEY_SECRET: str

    class Config:
        env_file = ".env"

# Log settings loading (redact sensitive values)
settings = Settings()
logger.info(f"[CONFIG] Settings loaded successfully")
logger.info(f"[CONFIG] Mongo URI: {settings.MONGO_URI[:10]}**** (redacted)")
logger.info(f"[CONFIG] JWT Secret: {settings.JWT_SECRET_KEY[:10]}**** (redacted)")
logger.info(f"[CONFIG] Razorpay Key ID: {settings.RAZORPAY_KEY_ID[:8]}**** (redacted)")
key_type = "TEST" if settings.RAZORPAY_KEY_ID.startswith("rzp_test_") else "LIVE" if settings.RAZORPAY_KEY_ID.startswith("rzp_live_") else "UNKNOWN"
logger.info(f"[CONFIG] Using Razorpay {key_type} keys")
logger.info(f"[CONFIG] Login OTP Required: {settings.LOGIN_OTP_REQUIRED}")
logger.info(f"[CONFIG] DO Spaces Endpoint: {settings.DO_SPACES_ENDPOINT}")
logger.info(f"[CONFIG] DO Spaces Bucket: {settings.DO_SPACES_BUCKET}")
logger.info(f"[CONFIG] SMTP Server: {settings.SMTP_SERVER}")
logger.info(f"[CONFIG] Sender Email: {settings.SENDER_EMAIL if settings.SENDER_EMAIL else 'None'}")
