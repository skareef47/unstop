"""
Core Application Configuration
"""
from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PROJECT_NAME: str = "PSAI — AI-Powered Technical Support & Troubleshooting Platform"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "psai-prototype-secret-key-change-in-production-1234567890"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Database: Supports SQLite (for tests/local) and PostgreSQL with pgvector
    DATABASE_URL: str = "sqlite:///./psai.db"

    # LLM Settings: "mock", "gemini", "openai", "groq"
    LLM_PROVIDER: str = "mock"
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    DEFAULT_LLM_MODEL: str = "gemini-2.5-flash"

    # Embedding Settings: "local", "gemini", "openai", "mock"
    EMBEDDING_PROVIDER: str = "local"
    EMBEDDING_DIMENSION: int = 384

    # CORS
    CORS_ORIGINS: Union[str, List[str]] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    # Security & Admin
    ADMIN_API_KEY: str = "psai-admin-secret-key-2026"
    ADMIN_EMAIL: str = "admin@psai.internal"
    ADMIN_PASSWORD: str = "adminpassword123"
    RATE_LIMIT_PER_MINUTE: int = 120
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB

    # Simulation Defaults
    SIMULATE_LATENCY_MS: int = 0


settings = Settings()
