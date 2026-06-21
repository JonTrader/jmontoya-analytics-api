from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


# Declarative base class for all SQLAlchemy models.
class Base(AsyncAttrs, DeclarativeBase):
    pass


# Async engine for the application.
# `echo=settings.debug` logs every SQL statement when debug mode is enabled.
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
)

# Factory for creating new async sessions.
# `expire_on_commit=False` keeps objects usable after a commit, which is the
# recommended behavior for async code.
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency that yields a database session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Create all tables defined by SQLAlchemy models.

    Used during application startup. The model import is deferred to avoid
    circular imports while the app is still being wired together.
    """
    from app import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
