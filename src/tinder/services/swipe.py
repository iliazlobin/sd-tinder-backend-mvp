"""Swipe service — record swipe actions and detect mutual matches."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tinder.models.match import Match
from tinder.models.swipe import Swipe


def _make_match_id(user_a: str, user_b: str) -> str:
    """Generate a deterministic match_id from sorted user pair."""
    return "".join(sorted([user_a, user_b]))


async def record_swipe(
    db: AsyncSession,
    swiper_id: str,
    swiped_id: str,
    decision: str,
) -> dict:
    """Record a swipe and check for mutual match.

    Returns:
        {"is_match": bool, "match_id": str | None}
    Raises:
        ValueError: if swiper_id == swiped_id (self-swipe)
    """
    if swiper_id == swiped_id:
        raise ValueError("Cannot swipe on yourself")

    # Check if already matched
    match_id = _make_match_id(swiper_id, swiped_id)
    existing_match = await db.execute(
        select(Match).where(
            Match.match_id == match_id,
            Match.is_active == True,  # noqa: E712
        )
    )
    if existing_match.scalar_one_or_none() is not None:
        raise MatchAlreadyExists(match_id)

    # Check if swipe already exists (idempotent — return existing result)
    existing_swipe = await db.execute(
        select(Swipe).where(
            Swipe.swiper_id == swiper_id,
            Swipe.swiped_id == swiped_id,
        )
    )
    swipe_row = existing_swipe.scalar_one_or_none()

    if swipe_row is not None:
        # Idempotent: return the existing swipe's result
        if swipe_row.decision != decision:
            return {"is_match": False, "match_id": None}
        # Same decision — proceed normally

    # Insert the swipe
    now = datetime.now(timezone.utc)
    if swipe_row is None:
        swipe = Swipe(
            swiper_id=swiper_id,
            swiped_id=swiped_id,
            decision=decision,
            created_at=now,
        )
        db.add(swipe)

    # If not a "like", no match possible
    if decision != "like":
        await db.commit()
        return {"is_match": False, "match_id": None}

    # Check for inverse swipe (the other user already liked this user)
    inverse = await db.execute(
        select(Swipe).where(
            Swipe.swiper_id == swiped_id,
            Swipe.swiped_id == swiper_id,
            Swipe.decision == "like",
        )
    )
    inverse_swipe = inverse.scalar_one_or_none()

    if inverse_swipe is not None:
        # Mutual like — create match
        match = Match(
            match_id=match_id,
            user_a=min(swiper_id, swiped_id),
            user_b=max(swiper_id, swiped_id),
            is_active=True,
            created_at=now,
        )
        db.add(match)
        await db.commit()
        return {"is_match": True, "match_id": match_id}

    await db.commit()
    return {"is_match": False, "match_id": None}


class MatchAlreadyExists(Exception):
    """Raised when trying to swipe on an already-matched user."""

    def __init__(self, match_id: str) -> None:
        self.match_id = match_id
        super().__init__(f"Already matched: {match_id}")
