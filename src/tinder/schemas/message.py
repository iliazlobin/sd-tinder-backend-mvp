"""Pydantic schemas for messaging."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class MessageSend(BaseModel):
    text: str = Field(..., min_length=1)


class MessageResponse(BaseModel):
    message_id: str
    match_id: str
    sender_id: str
    text: str
    created_at: datetime


class MessageListResponse(BaseModel):
    messages: list[MessageResponse]
    next_cursor: str | None = None
