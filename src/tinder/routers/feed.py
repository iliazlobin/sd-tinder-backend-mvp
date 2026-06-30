"""Feed router — candidate discovery endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from tinder.database import get_db
from tinder.schemas.feed import FeedResponse
from tinder.services.feed import get_feed
from tinder.services.redis_client import get_redis

router = APIRouter(prefix="/v1/feed", tags=["feed"])


@router.get("", response_model=FeedResponse)
async def feed(
    lat: float = Query(...),
    lon: float = Query(...),
    limit: int = Query(50, ge=1, le=100),
    x_user_id: str = Header(..., alias="X-User-Id"),
    db: AsyncSession = Depends(get_db),
) -> FeedResponse:
    """Get candidate profiles for the authenticated user."""
    redis = await get_redis()
    return await get_feed(db, redis, x_user_id, lat, lon, limit)
