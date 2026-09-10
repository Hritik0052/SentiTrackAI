"""User ORM model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.insight import Insight
    from app.models.journal_entry import JournalEntry
    from app.models.refresh_token import RefreshToken
    from app.models.streak_profile import StreakProfile
    from app.models.usage_event import UsageEvent
    from app.models.user_badge import UserBadge
    from app.models.user_challenge import UserChallenge
    from app.models.user_subscription import UserSubscription
    from app.models.weekly_summary import WeeklySummary
    from app.models.xp_profile import XpProfile


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_admin: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false"), default=False
    )

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    journals: Mapped[list["JournalEntry"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    weekly_summaries: Mapped[list["WeeklySummary"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    insights: Mapped[list["Insight"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    streak_profile: Mapped["StreakProfile | None"] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    xp_profile: Mapped["XpProfile | None"] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    badges: Mapped[list["UserBadge"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    challenges: Mapped[list["UserChallenge"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    subscription: Mapped["UserSubscription | None"] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    usage_events: Mapped[list["UsageEvent"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User id={self.id} email={self.email!r}>"
