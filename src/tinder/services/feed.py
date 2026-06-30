"""Feed service — generate candidate profiles for discovery."""

from __future__ import annotations

from sqlalchemy import and_, not_, select
from sqlalchemy.ext.asyncio import AsyncSession

from tinder.models.swipe import Swipe
from tinder.models.user import User
from tinder.schemas.feed import CandidateItem, FeedResponse
from tinder.services.geohash import distance_m, meters_to_km


async def get_feed(
    db: AsyncSession,
    redis,  # redis.asyncio.Redis | None
    user_id: str,
    lat: float,
    lon: float,
    limit: int = 50,
) -> FeedResponse:
    """Generate a feed of candidate profiles for the requesting user.

    Steps:
    1. Look up requesting user's preferences
    2. Find nearby users via geohash prefix (with Redis caching of geohash→user_ids)
    3. Filter by gender, age, distance
    4. Exclude already-swiped profiles
    5. Sort by distance
    """
    # Get requester's profile for preferences
    user_result = await db.execute(select(User).where(User.user_id == user_id))
    requester = user_result.scalar_one_or_none()

    # Default preferences if no profile or no preferences set
    prefs = (
        requester.preferences
        if requester and requester.preferences
        else {"gender": "everyone", "age_min": 18, "age_max": 99, "radius_km": 25}
    )

    # Compute bounding box for spatial query based on radius
    # Approximate degrees per km (rough but sufficient for initial filtering)
    km_per_deg_lat = 111.0
    km_per_deg_lon = 111.0 * 0.75  # Adjust for latitude (NYC ~40.7°N)
    
    radius_km = prefs.get("radius_km", 25)
    lat_delta = radius_km / km_per_deg_lat
    lon_delta = radius_km / km_per_deg_lon
    
    min_lat = lat - lat_delta
    max_lat = lat + lat_delta
    min_lon = lon - lon_delta
    max_lon = lon + lon_delta

    # Build query: users within bounding box, not the requester
    conditions = [
        User.user_id != user_id,
        User.lat >= min_lat,
        User.lat <= max_lat,
        User.lon >= min_lon,
        User.lon <= max_lon,
    ]

    # Gender filter
    preferred_gender = prefs.get("gender", "everyone")
    if preferred_gender != "everyone":
        conditions.append(User.gender == preferred_gender)

    # Age filter
    age_min = prefs.get("age_min", 18)
    age_max = prefs.get("age_max", 99)
    conditions.append(User.age >= age_min)
    conditions.append(User.age <= age_max)

    # Exclude already-swiped users
    swiped_sub = select(Swipe.swiped_id).where(Swipe.swiper_id == user_id)
    conditions.append(not_(User.user_id.in_(swiped_sub)))

    stmt = (
        select(User)
        .where(and_(*conditions))
        .limit(300)  # fetch more than needed to filter by distance
    )

    result = await db.execute(stmt)
    candidates_raw = result.scalars().all()

    # Filter by distance and compute distance_km
    max_distance_m = prefs.get("radius_km", 25) * 1000.0
    candidates: list[tuple[float, User]] = []
    for c in candidates_raw:
        dist_m = distance_m(lat, lon, c.lat, c.lon)
        if dist_m <= max_distance_m:
            candidates.append((dist_m, c))

    # Sort by distance
    candidates.sort(key=lambda x: x[0])

    # Build response
    items: list[CandidateItem] = []
    for dist_m, c in candidates[:limit]:
        items.append(
            CandidateItem(
                user_id=c.user_id,
                name=c.name,
                age=c.age,
                photos=c.photos,
                distance_km=round(meters_to_km(dist_m), 2),
            )
        )

    return FeedResponse(candidates=items)
