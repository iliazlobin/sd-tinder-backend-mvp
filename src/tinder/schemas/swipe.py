"""Pydantic schemas for the swipe endpoint."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SwipeRequest(BaseModel):
    swiped_id: str = Field(..., max_length=64)
    decision: Literal["like", "pass"]


class SwipeResponse(BaseModel):
    is_match: bool
    match_id: str | None = None
