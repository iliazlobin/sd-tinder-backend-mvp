"""Pydantic schemas for profile creation and response."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, model_validator


class PreferencesSchema(BaseModel):
    gender: str = "everyone"
    age_min: int = 18
    age_max: int = 99
    radius_km: int = 25


class ProfileCreate(BaseModel):
    name: str = Field(..., max_length=100)
    gender: Annotated[str, Field(...)]
    age: int = Field(..., ge=18)
    bio: str = ""
    photos: list[str] = Field(default_factory=list, max_length=9)
    lat: float
    lon: float
    preferences: PreferencesSchema | None = None

    @model_validator(mode="after")
    def validate_gender(self) -> "ProfileCreate":
        if self.gender not in ("men", "women", "everyone"):
            raise ValueError("gender must be 'men', 'women', or 'everyone'")
        return self

    @model_validator(mode="after")
    def clamp_radius(self) -> "ProfileCreate":
        if self.preferences:
            if self.preferences.radius_km < 1:
                self.preferences.radius_km = 1
            elif self.preferences.radius_km > 160:
                self.preferences.radius_km = 160
        return self


class ProfileResponse(BaseModel):
    user_id: str
    name: str
    gender: str
    age: int
    bio: str
    photos: list[str]
    lat: float
    lon: float
    preferences: PreferencesSchema | None = None
    created_at: datetime
    updated_at: datetime
