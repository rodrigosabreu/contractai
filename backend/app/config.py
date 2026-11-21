"""Application configuration using Pydantic Settings."""
import secrets
from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "ContractAI"
    APP_ENV: str = "development"
    DEBUG: bool = False  # SECURITY: False by default, must be explicitly enabled
    SECRET_KEY: str = Field(...)  # SECURITY: Required, no default - must be set via env
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # Redis / Celery
    REDIS_URL: str
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    CELERY_TASK_TRACK_STARTED: bool = True
    CELERY_TASK_TIME_LIMIT: int = 480
    CELERY_TASK_SOFT_TIME_LIMIT: int = 450
    CELERY_WORKER_PREFETCH_MULTIPLIER: int = 1
    CELERY_WORKER_MAX_TASKS_PER_CHILD: int = 100

    # LLM Providers
    OPENAI_API_KEY: Optional[str] = None
    NVIDIA_API_KEY: Optional[str] = None
    HERMES_BASE_URL: Optional[str] = None
    HERMES_API_KEY: Optional[str] = None
    HERMES_MODEL: str = "hermes-agent"
    DEFAULT_LLM_PROVIDER: str = "openai"
    OPENAI_MODEL: str = "gpt-4-turbo-preview"
    NVIDIA_MODEL: str = "nemotron-3-ultra"
    # SECURITY: LLM fallback between providers DISABLED by default
    LLM_FALLBACK_ENABLED: bool = False

    # Google Drive OAuth2
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/connectors/google/callback"
    GOOGLE_SCOPES: str = "https://www.googleapis.com/auth/drive.readonly"

    # OneDrive OAuth2
    MICROSOFT_CLIENT_ID: Optional[str] = None
    MICROSOFT_CLIENT_SECRET: Optional[str] = None
    MICROSOFT_TENANT_ID: str = "common"
    MICROSOFT_REDIRECT_URI: str = "http://localhost:8000/api/v1/connectors/onedrive/callback"
    MICROSOFT_SCOPES: str = "https://graph.microsoft.com/Files.Read"

    # File Storage
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: str = "pdf,docx,txt"
    UPLOAD_DIR: str = "/app/uploads"

    # LGPD / Compliance
    DATA_RETENTION_DAYS: int = 2555
    AUDIT_LOG_RETENTION_DAYS: int = 2555
    ANONYMIZE_ON_DELETE: bool = True

    # Monitoring
    PROMETHEUS_METRICS_ENABLED: bool = True
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000"

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate SECRET_KEY is strong enough."""
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v

    @field_validator("DEBUG")
    @classmethod
    def validate_debug_in_production(cls, v: bool, info) -> bool:
        """Warn if DEBUG=True in production."""
        # This validator runs before APP_ENV is validated, so we can't check it here
        # But we can add a model_validator to check the combination
        return v

    def model_post_init(self, __context) -> None:
        """Validate security-sensitive settings after initialization."""
        if self.is_production and self.DEBUG:
            import warnings
            warnings.warn(
                "DEBUG=True in production environment! This exposes sensitive information.",
                RuntimeWarning,
                stacklevel=2,
            )
        if self.is_production and self.LLM_FALLBACK_ENABLED:
            import warnings
            warnings.warn(
                "LLM_FALLBACK_ENABLED=True in production may send data to unauthorized providers!",
                RuntimeWarning,
                stacklevel=2,
            )

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.APP_ENV == "production"

    @property
    def database_url_async(self) -> str:
        """Return async database URL."""
        return self.DATABASE_URL

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins into list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    @property
    def allowed_extensions_list(self) -> List[str]:
        """Parse allowed extensions into list."""
        return [ext.strip().lower() for ext in self.ALLOWED_EXTENSIONS.split(",")]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()