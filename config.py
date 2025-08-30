from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    FRONTEND_URL: str = ""
    CORS_ORIGINS: str = "http://localhost:5173"
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"
    PROJECT_ROOT: str = ""
    
    class Config:
        env_file = ".env"

settings = Settings()