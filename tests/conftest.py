"""Test fixtures for the Tinder MVP test suite."""

from __future__ import annotations

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from tinder.main import create_app


@pytest_asyncio.fixture
async def client():
    """Async HTTP client for the FastAPI test app."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
