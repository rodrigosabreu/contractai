"""Database configuration and session management."""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool

from app.config import get_settings

settings = get_settings()


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


# SQLite configuration for development
def get_database_url() -> str:
    """Use the configured database in every environment."""
    url = make_url(settings.database_url_async)
    if url.drivername == "sqlite":
        url = url.set(drivername="sqlite+aiosqlite")
    return url.render_as_string(hide_password=False)


def get_engine() -> AsyncEngine:
    """Create engine with appropriate configuration."""
    url = get_database_url()
    
    if make_url(url).get_backend_name() == "sqlite":
        # SQLite specific configuration
        return create_async_engine(
            url,
            connect_args={"check_same_thread": False},
            **({"poolclass": StaticPool} if make_url(url).database in (None, "", ":memory:") else {}),
            echo=settings.DEBUG,
        )
    else:
        # PostgreSQL configuration
        return create_async_engine(
            url,
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            pool_pre_ping=True,
            echo=settings.DEBUG,
        )


engine: AsyncEngine = get_engine()

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database session."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database session outside of FastAPI."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database - runs migrations instead of create_all.
    
    In production, migrations should be run via: alembic upgrade head
    This function is kept for development convenience only.
    """
    # NOTE: In production, use: alembic upgrade head
    # This is kept for development convenience only
    if settings.APP_ENV != "production" and (settings.DEBUG or engine.dialect.name == "sqlite"):
        import app.models  # noqa: F401 - register models before creating tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()


async def check_db_connection() -> bool:
    """Check if database is accessible."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False