from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MONGO_URI: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SENDER_EMAIL: str | None = None
    SENDER_PASSWORD: str | None = None

    class Config:
        env_file = ".env"


settings = Settings()
