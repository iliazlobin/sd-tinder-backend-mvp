"""Messages router — send and list messages in a match."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from tinder.database import get_db
from tinder.schemas.message import MessageListResponse, MessageResponse, MessageSend
from tinder.services.message import list_messages, send_message

router = APIRouter(prefix="/v1/messages", tags=["messages"])


@router.post(
    "/{match_id}", response_model=MessageResponse, status_code=status.HTTP_201_CREATED
)
async def send_msg(
    match_id: str,
    payload: MessageSend,
    x_user_id: str = Header(..., alias="X-User-Id"),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Send a message in a match."""
    try:
        msg = await send_message(db, match_id, x_user_id, payload.text)
        return MessageResponse(
            message_id=msg.message_id,
            match_id=msg.match_id,
            sender_id=msg.sender_id,
            text=msg.text,
            created_at=msg.created_at,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{match_id}", response_model=MessageListResponse)
async def get_messages(
    match_id: str,
    before: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    x_user_id: str = Header(..., alias="X-User-Id"),
    db: AsyncSession = Depends(get_db),
) -> MessageListResponse:
    """List messages in a match, newest first, cursor-paginated."""
    try:
        return await list_messages(db, match_id, x_user_id, before=before, limit=limit)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
