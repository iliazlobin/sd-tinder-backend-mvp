"""Matches router — list matches and unmatch (soft delete)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from tinder.database import get_db
from tinder.schemas.match import MatchListResponse, UnmatchResponse
from tinder.services.match import get_match, list_matches

router = APIRouter(prefix="/v1/matches", tags=["matches"])


@router.get("", response_model=MatchListResponse)
async def list_my_matches(
    before: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    x_user_id: str = Header(..., alias="X-User-Id"),
    db: AsyncSession = Depends(get_db),
) -> MatchListResponse:
    """List active matches for the authenticated user."""
    return await list_matches(db, x_user_id, cursor=before, limit=limit)


@router.delete("/{match_id}", response_model=UnmatchResponse)
async def unmatch(
    match_id: str,
    x_user_id: str = Header(..., alias="X-User-Id"),
    db: AsyncSession = Depends(get_db),
) -> UnmatchResponse:
    """Soft-delete a match (unmatch). Only participants can unmatch."""
    match = await get_match(db, match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")
    if match.user_a != x_user_id and match.user_b != x_user_id:
        raise HTTPException(status_code=403, detail="Not a participant in this match")

    match.is_active = False
    await db.commit()
    return UnmatchResponse(unmatched=True)
