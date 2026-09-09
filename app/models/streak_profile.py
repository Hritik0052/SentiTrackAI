"""Streak profile: freezes + cached streak stats per user (Streaks 2.0)."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class StreakProfile(Base, TimestampMixin):
    __tablename__ = "streak_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    # Soft-streak freezes: miss a day without hard-resetting when tokens > 0.
    freeze_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    freezes_used_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Last calendar day a freeze was auto-applied (at most one per miss).
    last_freeze_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Cached values refreshed when streak status is computed / entry created.
    current_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    longest_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_entry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Highest streak length at which a freeze token was already granted (7, 14, 21…).
    freeze_earn_watermark: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    user: Mapped["User"] = relationship(back_populates="streak_profile")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<StreakProfile user_id={self.user_id} current={self.current_streak}>"
