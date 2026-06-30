"""Redis client — lazy singleton for caching and swiped-ID tracking."""

from __future__ import annotations

import redis.asyncio as aioredis

from tinder.config import settings

_redis = None


async def get_redis() -> aioredis.Redis:
    """Lazily create and return the async Redis client."""
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.redis_url, decode_responses=True, socket_connect_timeout=2
        )
    return _redis


async def close_redis() -> None:
    """Close the Redis connection pool."""
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
