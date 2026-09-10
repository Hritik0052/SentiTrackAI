"""Subscription plan catalog (Free, Pro, custom)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user_subscription import UserSubscription


class SubscriptionPlan(Base, TimestampMixin):
    __tablename__ = "subscription_plans"
    __table_args__ = (UniqueConstraint("code", name="uq_subscription_plans_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    daily_journal_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weekly_summary_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    daily_analyze_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weekly_insights_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)

    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false"), default=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true"), default=True
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0", default=0
    )

    # Phase 2 Cashfree-ready fields
    price_inr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    billing_period: Mapped[str | None] = mapped_column(String(32), nullable=True)
    cashfree_plan_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    subscriptions: Mapped[list["UserSubscription"]] = relationship(
        back_populates="plan",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<SubscriptionPlan id={self.id} code={self.code!r}>"
