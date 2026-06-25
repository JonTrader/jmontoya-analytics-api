import asyncio
import os
import subprocess
from collections.abc import AsyncGenerator
from urllib.parse import urlparse, urlunparse

import asyncpg
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import get_db
from app.main import app
from app.models import AnalyticsEvent


def _get_test_database_url() -> str:
    """Derive the test database URL from the configured DATABASE_URL."""
    parsed = urlparse(settings.database_url)
    return urlunparse(parsed._replace(path="/analytics_test"))


def _get_maintenance_database_url() -> str:
    """Return a URL for the 'postgres' maintenance database using asyncpg."""
    parsed = urlparse(settings.database_url)
    # asyncpg expects postgresql://, not the SQLAlchemy postgresql+asyncpg:// scheme.
    return urlunparse(parsed._replace(scheme="postgresql", path="/postgres"))


async def _create_test_database() -> None:
    """Create the analytics_test database if it does not already exist."""
    conn = await asyncpg.connect(_get_maintenance_database_url())
    try:
        await conn.execute("CREATE DATABASE analytics_test")
    except asyncpg.exceptions.DuplicateDatabaseError:
        pass
    finally:
        await conn.close()


def _apply_migrations() -> None:
    """Run Alembic migrations against the test database."""
    env = os.environ.copy()
    env["DATABASE_URL"] = _get_test_database_url()
    subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        env=env,
        check=True,
    )


@pytest.fixture(scope="session", autouse=True)
def setup_test_database() -> None:
    """Create the test database and apply migrations once per test session."""
    asyncio.run(_create_test_database())
    _apply_migrations()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession]:
    """Yield an async session bound to the test database engine."""
    engine = create_async_engine(
        _get_test_database_url(),
        echo=False,
        future=True,
    )
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with AsyncSessionLocal() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    """Yield an HTTP client with get_db overridden to use the test session."""

    async def override_get_db() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(autouse=True)
async def clean_events(db_session: AsyncSession) -> AsyncGenerator[None]:
    """Truncate analytics_events after each test to keep tests isolated."""
    yield
    await db_session.execute(delete(AnalyticsEvent))
    await db_session.commit()
