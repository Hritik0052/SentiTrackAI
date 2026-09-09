"""Individual XP award events."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.xp_profile import XpProfile


class XpEvent(Base, TimestampMixin):
    __tablename__ = "xp_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("xp_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)

    profile: Mapped["XpProfile"] = relationship(back_populates="events")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<XpEvent id={self.id} action={self.action!r} amount={self.amount}>"
