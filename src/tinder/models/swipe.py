"""Swipe model — record of a swipe action (like/pass)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from tinder.database import Base


class Swipe(Base):
    __tablename__ = "swipes"

    swiper_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.user_id"), primary_key=True
    )
    swiped_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.user_id"), primary_key=True
    )
    decision: Mapped[str] = mapped_column(String(4), nullable=False)  # 'like' or 'pass'
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
