from typing import List

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    FRONTEND_URL: str = ""
    CORS_ORIGINS: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30 # minutes
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7 # days
    ALGORITHM: str = "HS256"
    PROJECT_ROOT: str = ""
    OPENAI_API_KEY: str = ""

    AZURE_STORAGE_ACCOUNT_NAME: str
    AZURE_STORAGE_ACCOUNT_KEY: str
    AZURE_STORAGE_CONTAINER: str

    POSTGRES_CONNECTION_STRING: str = ""
    MONGO_URL: str = ""

    MAIL_MODE: str = ""
    MAIL_HOST: str = ""
    MAIL_PORT: int = 587
    MAIL_USER: str = ""
    MAIL_PASS: str = ""
    MAIL_USE_TLS: bool = True
    MAIL_FROM: str = ""

    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""

    class Config:
        env_file = ".env"

settings = Settings()