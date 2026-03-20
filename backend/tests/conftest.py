"""Shared fixtures for backend tests.

Integration test fixtures (client, db_engine, db_session) require dev dependencies:
  pip install -e ".[dev]"

Unit tests (test_parser.py) work without these fixtures.
"""

import asyncio
from unittest.mock import patch

import pytest

try:
    import pytest_asyncio
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    _HAS_INTEGRATION_DEPS = True
except ImportError:
    _HAS_INTEGRATION_DEPS = False


# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///file::memory:?cache=shared&uri=true"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


if _HAS_INTEGRATION_DEPS:
    from backend.app.main import app
    from backend.app.database import get_db
    from backend.app.models import Base

    @pytest_asyncio.fixture
    async def db_engine():
        engine = create_async_engine(TEST_DATABASE_URL, echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        yield engine
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    @pytest_asyncio.fixture
    async def db_session(db_engine):
        session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
        async with session_factory() as session:
            yield session

    @pytest_asyncio.fixture
    async def client(db_engine):
        """Async test client with DB override."""
        session_factory = async_sessionmaker(db_engine, expire_on_commit=False)

        async def override_get_db():
            async with session_factory() as session:
                yield session

        app.dependency_overrides[get_db] = override_get_db

        # Mock agent_manager to avoid loading Biomni
        with patch("backend.app.services.agent_manager._agent_ready", True), \
             patch("backend.app.services.agent_manager._celery_patched", True):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                yield ac

        app.dependency_overrides.clear()
