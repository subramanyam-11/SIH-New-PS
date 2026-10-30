import os
from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DEMO_MODE: bool = True
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/aicte_workflow"
    
    # Auth
    JWT_SECRET: str = "super-secret-key-change-in-production-aicte-2026-sih"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    
    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001"
    
    # LLM
    LLM_PROVIDER: str = "none"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gemini-1.5-flash"
    LLM_TIMEOUT_SECONDS: int = 10
    
    # Email Outbox & SMTP
    EMAIL_SEND_ENABLED: bool = False
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "no-reply@aicte-india.org"
    SMTP_TLS: bool = False

    # File Storage & Security
    FILE_ENCRYPTION_KEY: str = "b64:k8V9H9eY6j2Rz+1wT8g4P0L6n+M4q1A3u5Y7c9e0w2I="  # 32-byte AES key
    FILE_ENCRYPTION_KEY_ID: str = "key_v1"
    CLAMAV_HOST: str = ""
    CLAMAV_PORT: int = 3310
    MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB

    # Login Security & Rate Limiting
    LOGIN_MAX_FAILED_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15

    # Mock AICTE Integration
    INTEGRATION_API_KEY: str = "aicte-sandbox-api-key-2026-secret"
    INTEGRATION_HMAC_SECRET: str = "aicte-hmac-sha256-signing-secret-2026"

    # Scheduler
    SCHEDULER_ENABLED: bool = True
    SCHEDULER_INTERVAL_MINUTES: int = 5

    # Risk Scoring Centralized Thresholds
    # Low: < 40 (0-39), Medium: 40-69, High: >= 70
    RISK_LOW_MAX: int = 39
    RISK_MEDIUM_MAX: int = 69

    @property
    def RISK_BAND_THRESHOLDS(self) -> dict:
        return {"low_max": self.RISK_LOW_MAX, "medium_max": self.RISK_MEDIUM_MAX}

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]


settings = Settings()
