"""Test configuration and settings."""
import pytest
from app.config import Settings


def test_settings_defaults():
    """Test default settings values."""
    settings = Settings(
        DATABASE_URL="postgresql+asyncpg://test:test@localhost/test",
        REDIS_URL="redis://localhost:6379/0",
        SECRET_KEY="a" * 32,
    )
    assert settings.APP_NAME == "ContractAI"
    assert settings.ALGORITHM == "HS256"
    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30
    assert settings.REFRESH_TOKEN_EXPIRE_DAYS == 7
    assert settings.DEBUG is False  # Security: False by default
    assert settings.LLM_FALLBACK_ENABLED is False  # Security: False by default


def test_settings_secret_key_validation():
    """Test SECRET_KEY validation."""
    with pytest.raises(ValueError):
        Settings(
            DATABASE_URL="postgresql+asyncpg://test:test@localhost/test",
            REDIS_URL="redis://localhost:6379/0",
            SECRET_KEY="short",  # Too short
        )


def test_settings_cors_parsing():
    """Test CORS origins parsing."""
    settings = Settings(
        DATABASE_URL="postgresql+asyncpg://test:test@localhost/test",
        REDIS_URL="redis://localhost:6379/0",
        SECRET_KEY="a" * 32,
        CORS_ORIGINS="http://localhost:3000, http://localhost:8000,https://app.example.com",
    )
    origins = settings.cors_origins_list
    assert len(origins) == 3
    assert "http://localhost:3000" in origins
    assert "http://localhost:8000" in origins
    assert "https://app.example.com" in origins


def test_settings_allowed_extensions_parsing():
    """Test allowed extensions parsing."""
    settings = Settings(
        DATABASE_URL="postgresql+asyncpg://test:test@localhost/test",
        REDIS_URL="redis://localhost:6379/0",
        SECRET_KEY="a" * 32,
        ALLOWED_EXTENSIONS="pdf, docx, TXT, PDF",
    )
    extensions = settings.allowed_extensions_list
    assert len(extensions) == 4
    assert "pdf" in extensions
    assert "docx" in extensions
    assert "txt" in extensions