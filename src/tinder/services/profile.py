"""Profile service — create, update, read user profiles."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tinder.models.user import User
from tinder.schemas.profile import PreferencesSchema, ProfileCreate, ProfileResponse
from tinder.services.geohash import encode as encode_geohash


def _clamp_preferences(prefs: PreferencesSchema | None) -> dict | None:
    """Clamp radius_km to 1–160 and return as dict, or None."""
    if prefs is None:
        return None
    radius = prefs.radius_km
    radius = max(1, min(160, radius))
    return {
        "gender": prefs.gender,
        "age_min": prefs.age_min,
        "age_max": prefs.age_max,
        "radius_km": radius,
    }


async def upsert_profile(
    db: AsyncSession,
    user_id: str,
    payload: ProfileCreate,
) -> User:
    """Create or update a user profile. Returns the User ORM object."""
    now = datetime.now(timezone.utc)
    geohash = encode_geohash(payload.lat, payload.lon, precision=7)
    prefs = _clamp_preferences(payload.preferences)

    # SELECT-then-UPDATE/INSERT — cross-dialect compatible
    existing = await get_profile(db, user_id)
    if existing:
        existing.name = payload.name
        existing.gender = payload.gender
        existing.age = payload.age
        existing.bio = payload.bio
        existing.photos = payload.photos
        existing.lat = payload.lat
        existing.lon = payload.lon
        existing.geohash = geohash
        existing.preferences = prefs or {}
        existing.updated_at = now
        await db.commit()
        return existing

    user = User(
        user_id=user_id,
        name=payload.name,
        gender=payload.gender,
        age=payload.age,
        bio=payload.bio,
        photos=payload.photos,
        lat=payload.lat,
        lon=payload.lon,
        geohash=geohash,
        preferences=prefs or {},
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    await db.commit()
    return user


async def get_profile(db: AsyncSession, user_id: str) -> User | None:
    """Get a user profile by ID."""
    result = await db.execute(select(User).where(User.user_id == user_id))
    return result.scalar_one_or_none()


def user_to_response(user: User) -> ProfileResponse:
    """Convert a User ORM object to a ProfileResponse."""
    return ProfileResponse(
        user_id=user.user_id,
        name=user.name,
        gender=user.gender,
        age=user.age,
        bio=user.bio,
        photos=user.photos,
        lat=user.lat,
        lon=user.lon,
        preferences=PreferencesSchema(**user.preferences) if user.preferences else None,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )
