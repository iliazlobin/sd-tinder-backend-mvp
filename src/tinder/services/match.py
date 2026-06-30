"""Match service — list matches with cursor-based pagination."""

from __future__ import annotations

import base64
from datetime import datetime, timezone

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from tinder.models.match import Match
from tinder.models.user import User
from tinder.schemas.match import MatchItem, MatchListResponse, OtherUser


def _encode_cursor(dt: datetime) -> str:
    """Encode a datetime to a cursor string (base64 of ISO timestamp)."""
    return base64.urlsafe_b64encode(dt.isoformat().encode()).decode()


def _decode_cursor(cursor: str) -> datetime:
    """Decode a cursor string back to a datetime."""
    iso = base64.urlsafe_b64decode(cursor.encode()).decode()
    if "+" in iso or iso.endswith("Z"):
        return datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return datetime.fromisoformat(iso).replace(tzinfo=timezone.utc)


async def list_matches(
    db: AsyncSession,
    user_id: str,
    cursor: str | None = None,
    limit: int = 20,
) -> MatchListResponse:
    """Return cursor-paginated active matches for a user with last-message preview."""
    stmt = (
        select(Match)
        .where(
            Match.is_active == True,  # noqa: E712
            or_(Match.user_a == user_id, Match.user_b == user_id),
        )
        .order_by(Match.last_message_at.desc().nullslast(), Match.created_at.desc())
        .limit(limit + 1)  # fetch one extra to detect if there's a next page
    )

    if cursor:
        cursor_dt = _decode_cursor(cursor)
        # For matches with last_message_at, filter by it; otherwise by created_at
        stmt = stmt.where(
            or_(
                and_(
                    Match.last_message_at.isnot(None), Match.last_message_at < cursor_dt
                ),
                and_(Match.last_message_at.is_(None), Match.created_at < cursor_dt),
            )
        )

    result = await db.execute(stmt)
    matches = result.scalars().all()

    # Check if there's a next page
    has_next = len(matches) > limit
    matches = matches[:limit]

    items: list[MatchItem] = []
    for m in matches:
        other_id = m.user_b if m.user_a == user_id else m.user_a
        # Fetch other user's name + photo
        user_res = await db.execute(select(User).where(User.user_id == other_id))
        other_user = user_res.scalar_one_or_none()

        items.append(
            MatchItem(
                match_id=m.match_id,
                other_user=OtherUser(
                    id=other_id,
                    name=other_user.name if other_user else "Unknown",
                    photos=other_user.photos if other_user else [],
                ),
                last_message_at=m.last_message_at,
                preview_text=m.preview_text or "",
            )
        )

    next_cursor = None
    if has_next and items:
        # Use the last item's sort key
        last_match = matches[-1]
        sort_dt = last_match.last_message_at or last_match.created_at
        next_cursor = _encode_cursor(sort_dt)

    return MatchListResponse(
        matches=items,
        next_cursor=next_cursor,
    )


async def get_match(db: AsyncSession, match_id: str) -> Match | None:
    """Get a match by ID."""
    result = await db.execute(select(Match).where(Match.match_id == match_id))
    return result.scalar_one_or_none()


async def update_match_preview(
    db: AsyncSession,
    match_id: str,
    preview_text: str,
    last_message_at,
) -> None:
    """Update match preview text and last message timestamp."""
    match = await get_match(db, match_id)
    if match:
        match.preview_text = preview_text
        match.last_message_at = last_message_at
        await db.commit()
