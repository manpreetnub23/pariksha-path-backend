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

    class Config:
        env_file = ".env"


settings = Settings()
