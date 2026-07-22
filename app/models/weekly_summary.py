"""WeeklySummary ORM model: one AI digest per user per week."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Date, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class WeeklySummary(Base, TimestampMixin):
    __tablename__ = "weekly_summaries"
    # At most one summary per user per week; regenerating upserts this row.
    __table_args__ = (
        UniqueConstraint("user_id", "week_start", name="uq_weekly_summaries_user_id_week_start"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Monday (week_start) through Sunday (week_end) of the summarized week.
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    week_end: Mapped[date] = mapped_column(Date, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    # List of short suggestion strings, stored as JSON (portable across SQLite/PG).
    suggestions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    entry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    user: Mapped["User"] = relationship(back_populates="weekly_summaries")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<WeeklySummary id={self.id} user_id={self.user_id} week_start={self.week_start}>"
