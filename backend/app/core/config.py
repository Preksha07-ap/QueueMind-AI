import os
from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")


class Settings(BaseSettings):
    """
    Application configuration settings loaded from environment variables
    or defaults.
    """
    model_config = SettingsConfigDict(
        env_file=(_ENV_FILE, ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # General Project Information
    PROJECT_NAME: str = "QueueMind AI - Intelligent IT Helpdesk Management System"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # CORS Settings
    CORS_ORIGINS: Union[List[str], str] = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:5174,http://127.0.0.1:5174,"
        "http://localhost:3000,http://127.0.0.1:3000"
    )

    @property
    def cors_origins_list(self) -> List[str]:
        if isinstance(self.CORS_ORIGINS, list):
            return self.CORS_ORIGINS
        cleaned = self.CORS_ORIGINS.strip().strip('"').strip("'")
        return [origin.strip().strip('"').strip("'") for origin in cleaned.split(",") if origin.strip()]

    # MySQL Database Configuration
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "queuemind_user"
    DB_PASSWORD: str = "your_secure_password_here"
    DB_NAME: str = "queuemind_db"

    @property
    def database_url(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # JWT Authentication Configuration
    JWT_SECRET_KEY: str = "queuemind-dev-insecure-secret-key-change-in-production-2026"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours for development

    # Future AI / Vector Engine Configuration
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:7b"
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333


settings = Settings()
