"""Pydantic schemas for match list and unmatch."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class OtherUser(BaseModel):
    id: str
    name: str
    photos: list[str]


class MatchItem(BaseModel):
    match_id: str
    other_user: OtherUser
    last_message_at: datetime | None = None
    preview_text: str | None = None


class MatchListResponse(BaseModel):
    matches: list[MatchItem]
    next_cursor: str | None = None


class UnmatchResponse(BaseModel):
    unmatched: bool = True
