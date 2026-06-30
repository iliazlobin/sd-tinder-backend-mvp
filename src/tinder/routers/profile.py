"""Profile router — create/update profile endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from tinder.database import get_db
from tinder.schemas.profile import ProfileCreate, ProfileResponse
from tinder.services.profile import get_profile, upsert_profile, user_to_response

router = APIRouter(prefix="/v1/profile", tags=["profile"])


@router.post("/me", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_or_update_profile(
    payload: ProfileCreate,
    x_user_id: str = Header(..., alias="X-User-Id"),
    db: AsyncSession = Depends(get_db),
) -> ProfileResponse:
    """Create or update the authenticated user's profile."""
    user = await upsert_profile(db, x_user_id, payload)
    return user_to_response(user)


@router.get("/me", response_model=ProfileResponse)
async def get_my_profile(
    x_user_id: str = Header(..., alias="X-User-Id"),
    db: AsyncSession = Depends(get_db),
) -> ProfileResponse:
    """Get the authenticated user's profile."""
    user = await get_profile(db, x_user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return user_to_response(user)
