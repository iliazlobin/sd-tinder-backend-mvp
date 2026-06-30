"""Shared fixtures and helpers for the black-box acceptance suite.

These tests do NOT import `src.tinder`. They talk to the running system
via HTTP at API_BASE_URL.
"""

import os
import pytest
import httpx
import asyncio


API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")


@pytest.fixture(scope="session")
def base_url():
    return API_BASE_URL


@pytest.fixture(scope="session")
def client(base_url):
    """Session-scoped httpx client for the entire acceptance run."""
    with httpx.Client(base_url=base_url, timeout=10) as c:
        yield c


@pytest.fixture(autouse=True)
def clear_database():
    """Clear all tables before each test to ensure isolation."""
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
    from tinder.database import get_engine
    from sqlalchemy import text

    async def _clear():
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.execute(text('DELETE FROM messages'))
            await conn.execute(text('DELETE FROM matches'))
            await conn.execute(text('DELETE FROM swipes'))
            await conn.execute(text('DELETE FROM users'))
        await engine.dispose()

    asyncio.run(_clear())
    yield


@pytest.fixture
def fresh_user_id():
    """Generate a unique user_id for each test. In MVP, user_ids are
    client-provided ULIDs. We use a counter-based scheme for simplicity
    in black-box acceptance tests — the system only cares about uniqueness
    and the 26-char ULID format constraint."""
    import uuid
    return str(uuid.uuid4())[:26]


# --- Helper assertions ---

def assert_json_200(r, expected_status=200):
    """Assert status and return parsed JSON."""
    assert r.status_code == expected_status, \
        f"Expected {expected_status}, got {r.status_code}: {r.text}"
    return r.json()


def assert_201(r):
    return assert_json_200(r, 201)


def assert_422(r):
    assert r.status_code == 422, \
        f"Expected 422, got {r.status_code}: {r.text}"
    return r.json()


def assert_404(r):
    assert r.status_code == 404, \
        f"Expected 404, got {r.status_code}: {r.text}"
    return r.json()


def assert_403(r):
    assert r.status_code == 403, \
        f"Expected 403, got {r.status_code}: {r.text}"
    return r.json()


def assert_409(r):
    assert r.status_code == 409, \
        f"Expected 409, got {r.status_code}: {r.text}"
    return r.json()


# --- Profile creation helper ---

def create_profile(client, user_id, **overrides):
    """Create a profile and return the parsed response body.
    Default values are valid; override any field."""
    defaults = {
        "name": f"User-{user_id[:6]}",
        "gender": "men",
        "age": 25,
        "bio": "Test bio",
        "photos": [],
        "lat": 40.7128,
        "lon": -74.0060,
    }
    defaults.update(overrides)
    r = client.post(
        "/v1/profile/me",
        json={**defaults},
        headers={"X-User-Id": user_id},
    )
    return assert_201(r)
