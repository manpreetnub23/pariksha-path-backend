from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    MONGO_URI: str

    # JWT Authentication
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int

    # Email configuration
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 465  # SSL port (alternative: 587 for STARTTLS)
    SENDER_EMAIL: str | None = None
    SENDER_PASSWORD: str | None = None  # App password should not have spaces

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
    
    # Razorpay configuration
     # 👇 Add Razorpay keys here
    RAZORPAY_KEY_ID: str
    RAZORPAY_KEY_SECRET: str


    class Config:
        env_file = ".env"


settings = Settings()
