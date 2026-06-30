"""Message service — send and list messages with cursor pagination."""

from __future__ import annotations

import base64
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tinder.models.match import Match
from tinder.models.message import Message
from tinder.schemas.message import MessageListResponse, MessageResponse


def _encode_cursor(dt: datetime) -> str:
    """Encode a datetime to a cursor string (base64 of ISO timestamp)."""
    return base64.urlsafe_b64encode(dt.isoformat().encode()).decode()


def _decode_cursor(cursor: str) -> datetime:
    """Decode a cursor string back to a datetime."""
    iso = base64.urlsafe_b64decode(cursor.encode()).decode()
    if "+" in iso or iso.endswith("Z"):
        return datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return datetime.fromisoformat(iso).replace(tzinfo=timezone.utc)


async def send_message(
    db: AsyncSession,
    match_id: str,
    sender_id: str,
    text: str,
) -> Message:
    """Send a message in a match. Raises ValueError if not a participant."""
    # Verify match exists and user is a participant
    result = await db.execute(select(Match).where(Match.match_id == match_id))
    match = result.scalar_one_or_none()
    if match is None:
        raise ValueError("Match not found")
    if match.user_a != sender_id and match.user_b != sender_id:
        raise PermissionError("Not a participant in this match")
    if not match.is_active:
        raise ValueError("Match is no longer active")

    now = datetime.now(timezone.utc)
    message = Message(
        message_id=str(uuid.uuid4()),
        match_id=match_id,
        sender_id=sender_id,
        text=text,
        created_at=now,
    )
    db.add(message)

    # Update match preview
    match.preview_text = text[:100]
    match.last_message_at = now

    await db.commit()
    return message


async def list_messages(
    db: AsyncSession,
    match_id: str,
    user_id: str,
    before: str | None = None,
    limit: int = 20,
) -> MessageListResponse:
    """List messages in a match, newest first, cursor-paginated.

    Args:
        before: cursor (base64-encoded ISO timestamp) to page before
        limit: max messages to return (default 20)
    """
    # Verify user is a participant
    result = await db.execute(select(Match).where(Match.match_id == match_id))
    match = result.scalar_one_or_none()
    if match is None:
        raise ValueError("Match not found")
    if match.user_a != user_id and match.user_b != user_id:
        raise PermissionError("Not a participant in this match")

    stmt = (
        select(Message)
        .where(Message.match_id == match_id)
        .order_by(Message.created_at.desc())
        .limit(limit + 1)  # fetch one extra to detect next page
    )

    if before:
        cursor_dt = _decode_cursor(before)
        stmt = stmt.where(Message.created_at < cursor_dt)

    result = await db.execute(stmt)
    messages = result.scalars().all()

    has_next = len(messages) > limit
    messages = messages[:limit]

    items = [
        MessageResponse(
            message_id=m.message_id,
            match_id=m.match_id,
            sender_id=m.sender_id,
            text=m.text,
            created_at=m.created_at,
        )
        for m in messages
    ]

    next_cursor = None
    if has_next and items:
        next_cursor = _encode_cursor(items[-1].created_at)

    return MessageListResponse(
        messages=items,
        next_cursor=next_cursor,
    )
