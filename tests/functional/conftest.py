"""Fixtures for functional tests — real PostgreSQL, ASGI transport.

Creates a fresh engine per test and disposes it after to avoid
event-loop conflicts with SQLAlchemy's async engine across tests.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from tinder.main import create_app


@pytest.fixture
async def client():
    """Async HTTP client — creates fresh app+engine, disposes after test."""
    import tinder.database as db_mod

    # Reset engine globals so get_engine() creates a fresh engine for this test
    if db_mod._engine is not None:
        await db_mod._engine.dispose()
    db_mod._engine = None
    db_mod._session_factory = None

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # After test: dispose the engine so next test gets a fresh one
    if db_mod._engine is not None:
        await db_mod._engine.dispose()
        db_mod._engine = None
        db_mod._session_factory = None
