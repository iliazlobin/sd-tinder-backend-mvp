"""SQLAlchemy models package — re-exports all models for Alembic."""

from tinder.models.user import User
from tinder.models.swipe import Swipe
from tinder.models.match import Match
from tinder.models.message import Message

__all__ = ["User", "Swipe", "Match", "Message"]
