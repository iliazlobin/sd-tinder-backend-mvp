"""Pydantic schemas package."""

from tinder.schemas.profile import PreferencesSchema, ProfileCreate, ProfileResponse
from tinder.schemas.feed import CandidateItem, FeedResponse
from tinder.schemas.swipe import SwipeRequest, SwipeResponse
from tinder.schemas.match import (
    MatchItem,
    MatchListResponse,
    OtherUser,
    UnmatchResponse,
)
from tinder.schemas.message import MessageSend, MessageResponse, MessageListResponse

__all__ = [
    "PreferencesSchema",
    "ProfileCreate",
    "ProfileResponse",
    "CandidateItem",
    "FeedResponse",
    "SwipeRequest",
    "SwipeResponse",
    "MatchItem",
    "MatchListResponse",
    "OtherUser",
    "UnmatchResponse",
    "MessageSend",
    "MessageResponse",
    "MessageListResponse",
]
