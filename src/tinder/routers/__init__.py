"""Routers package — aggregates all endpoint routers."""

from tinder.routers.profile import router as profile_router
from tinder.routers.feed import router as feed_router
from tinder.routers.swipe import router as swipe_router
from tinder.routers.matches import router as matches_router
from tinder.routers.messages import router as messages_router

__all__ = [
    "profile_router",
    "feed_router",
    "swipe_router",
    "matches_router",
    "messages_router",
]
