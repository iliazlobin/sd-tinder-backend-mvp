"""Swipe router — record swipe and detect mutual match."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from tinder.database import get_db
from tinder.schemas.swipe import SwipeRequest, SwipeResponse
from tinder.services.swipe import MatchAlreadyExists, record_swipe

router = APIRouter(prefix="/v1/swipe", tags=["swipe"])


@router.post("", response_model=SwipeResponse, status_code=status.HTTP_200_OK)
async def swipe(
    payload: SwipeRequest,
    x_user_id: str = Header(..., alias="X-User-Id"),
    db: AsyncSession = Depends(get_db),
) -> SwipeResponse:
    """Record a swipe and check for mutual match."""
    try:
        result = await record_swipe(db, x_user_id, payload.swiped_id, payload.decision)
        return SwipeResponse(**result)
    except MatchAlreadyExists as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Already matched: {e.match_id}",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
