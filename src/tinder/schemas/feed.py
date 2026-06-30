"""Pydantic schemas for the feed endpoint."""

from __future__ import annotations

from pydantic import BaseModel


class CandidateItem(BaseModel):
    user_id: str
    name: str
    age: int
    photos: list[str]
    distance_km: float


class FeedResponse(BaseModel):
    candidates: list[CandidateItem]
