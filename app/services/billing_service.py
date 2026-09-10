"""Subscription plans, assignment, and quota enforcement."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models.journal_entry import JournalEntry
from app.models.subscription_plan import SubscriptionPlan
from app.models.usage_event import UsageEvent
from app.models.user import User
from app.models.user_subscription import UserSubscription
from app.schemas.billing import (
    PlanCreate,
    PlanSummary,
    PlanUpdate,
    QuotaBucket,
    UsageSnapshot,
)

ACTION_ANALYZE = "analyze"
ACTION_WEEKLY_SUMMARY = "weekly_summary"
ACTION_INSIGHTS = "insights_generate"
ACTION_JOURNAL = "journal_create"

_ACTION_LABELS = {
    ACTION_JOURNAL: "Daily journal",
    ACTION_ANALYZE: "Daily analyze",
    ACTION_WEEKLY_SUMMARY: "Weekly summary",
    ACTION_INSIGHTS: "Weekly insights",
}


def _now() -> datetime:
    return datetime.utcnow()


def plan_duration_days(plan: SubscriptionPlan) -> int:
    """Validity window in days. Admin-editable; sensible defaults by billing_period."""
    if plan.duration_days is not None and plan.duration_days > 0:
        return int(plan.duration_days)
    period = (plan.billing_period or "").lower()
    if period in ("trial", "free"):
        return 15
    if period == "yearly":
        return 365
    return 30


def compute_ends_at(starts_at: datetime, plan: SubscriptionPlan) -> datetime:
    return starts_at + timedelta(days=plan_duration_days(plan))


def is_subscription_expired(sub: UserSubscription, *, now: datetime | None = None) -> bool:
    if sub.ends_at is None:
        return False
    return sub.ends_at <= (now or _now())


def apply_subscription_window(
    sub: UserSubscription,
    plan: SubscriptionPlan,
    *,
    renew_extend: bool = False,
) -> None:
    """Set starts_at / ends_at from plan.duration_days.

    If renew_extend and the same plan is still active with future ends_at,
    extend from ends_at (stack another period). Otherwise start a fresh window.
    """
    now = _now()
    days = plan_duration_days(plan)
    if (
        renew_extend
        and sub.plan_id == plan.id
        and sub.status == "active"
        and sub.ends_at is not None
        and sub.ends_at > now
    ):
        sub.starts_at = sub.starts_at or now
        sub.ends_at = sub.ends_at + timedelta(days=days)
        return
    sub.starts_at = now
    sub.ends_at = now + timedelta(days=days)


def _day_bounds(day: date | None = None) -> tuple[datetime, datetime]:
    # Naive datetimes match SQLite / TimestampMixin server defaults used elsewhere.
    d = day or date.today()
    start = datetime.combine(d, time.min)
    end = datetime.combine(d, time.max)
    return start, end


def _week_bounds(day: date | None = None) -> tuple[datetime, datetime]:
    d = day or date.today()
    week_start = d - timedelta(days=d.weekday())
    week_end = week_start + timedelta(days=6)
    start = datetime.combine(week_start, time.min)
    end = datetime.combine(week_end, time.max)
    return start, end


def get_default_plan(db: Session) -> SubscriptionPlan:
    plan = db.scalar(
        select(SubscriptionPlan).where(
            SubscriptionPlan.is_default.is_(True),
            SubscriptionPlan.is_active.is_(True),
        )
    )
    if plan is None:
        raise NotFoundError("No default subscription plan configured")
    return plan


def get_plan(db: Session, plan_id: int) -> SubscriptionPlan:
    plan = db.get(SubscriptionPlan, plan_id)
    if plan is None:
        raise NotFoundError("Subscription plan not found")
    return plan


def get_user_subscription(db: Session, user_id: int) -> UserSubscription | None:
    return db.scalar(
        select(UserSubscription)
        .options(joinedload(UserSubscription.plan))
        .where(UserSubscription.user_id == user_id)
    )


def get_user_plan(db: Session, user_id: int) -> SubscriptionPlan | None:
    sub = get_user_subscription(db, user_id)
    if sub is None or sub.status != "active":
        return None
    if is_subscription_expired(sub):
        sub.status = "expired"
        db.commit()
        return None
    return sub.plan


def assign_default_plan(db: Session, user: User, *, commit: bool = False) -> UserSubscription:
    existing = get_user_subscription(db, user.id)
    if existing is not None:
        return existing
    plan = get_default_plan(db)
    now = _now()
    sub = UserSubscription(
        user_id=user.id,
        plan_id=plan.id,
        status="active",
        starts_at=now,
        ends_at=compute_ends_at(now, plan),
        payment_provider="manual",
    )
    db.add(sub)
    if commit:
        db.commit()
        db.refresh(sub)
    else:
        db.flush()
    return sub


def assign_plan(
    db: Session,
    user: User,
    plan: SubscriptionPlan,
    *,
    notes: str | None = None,
    status: str = "active",
    renew_extend: bool = False,
    commit: bool = True,
) -> UserSubscription:
    if not plan.is_active and status == "active":
        raise BadRequestError("Cannot assign an inactive plan")
    sub = get_user_subscription(db, user.id)
    if sub is None:
        sub = UserSubscription(user_id=user.id, plan_id=plan.id)
        db.add(sub)
    if status == "active":
        apply_subscription_window(sub, plan, renew_extend=renew_extend)
    sub.plan_id = plan.id
    sub.status = status
    if notes is not None:
        sub.notes = notes
    sub.payment_provider = sub.payment_provider or "manual"
    if commit:
        db.commit()
        db.refresh(sub)
    else:
        db.flush()
    return sub

def list_plans(db: Session, *, active_only: bool = False) -> list[SubscriptionPlan]:
    stmt = select(SubscriptionPlan).order_by(
        SubscriptionPlan.sort_order.asc(), SubscriptionPlan.id.asc()
    )
    if active_only:
        stmt = stmt.where(SubscriptionPlan.is_active.is_(True))
    return list(db.scalars(stmt).all())


def create_plan(db: Session, payload: PlanCreate) -> SubscriptionPlan:
    existing = db.scalar(select(SubscriptionPlan).where(SubscriptionPlan.code == payload.code))
    if existing is not None:
        raise ConflictError("Plan code already exists")
    plan = SubscriptionPlan(**payload.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def update_plan(db: Session, plan: SubscriptionPlan, payload: PlanUpdate) -> SubscriptionPlan:
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(plan, key, value)
    db.commit()
    db.refresh(plan)
    return plan


def set_default_plan(db: Session, plan: SubscriptionPlan) -> SubscriptionPlan:
    if not plan.is_active:
        raise BadRequestError("Default plan must be active")
    others = list(db.scalars(select(SubscriptionPlan).where(SubscriptionPlan.is_default.is_(True))).all())
    for other in others:
        other.is_default = False
    plan.is_default = True
    db.commit()
    db.refresh(plan)
    return plan


def _count_journals_today(db: Session, user_id: int) -> int:
    start, end = _day_bounds()
    return (
        db.scalar(
            select(func.count())
            .select_from(JournalEntry)
            .where(
                JournalEntry.user_id == user_id,
                JournalEntry.created_at >= start,
                JournalEntry.created_at <= end,
            )
        )
        or 0
    )


def _count_usage_events(
    db: Session, user_id: int, action: str, start: datetime, end: datetime
) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(UsageEvent)
            .where(
                UsageEvent.user_id == user_id,
                UsageEvent.action == action,
                UsageEvent.created_at >= start,
                UsageEvent.created_at <= end,
            )
        )
        or 0
    )


def _bucket(used: int, limit: int | None) -> QuotaBucket:
    remaining = None if limit is None else max(limit - used, 0)
    return QuotaBucket(used=used, limit=limit, remaining=remaining)


def get_usage_snapshot(db: Session, user_id: int) -> UsageSnapshot:
    plan = get_user_plan(db, user_id)
    day_start, day_end = _day_bounds()
    week_start, week_end = _week_bounds()

    journals_used = _count_journals_today(db, user_id)
    analyze_used = _count_usage_events(db, user_id, ACTION_ANALYZE, day_start, day_end)
    summary_used = _count_usage_events(
        db, user_id, ACTION_WEEKLY_SUMMARY, week_start, week_end
    )
    insights_used = _count_usage_events(db, user_id, ACTION_INSIGHTS, week_start, week_end)

    return UsageSnapshot(
        plan=to_plan_summary(plan),
        journals_today=_bucket(
            journals_used, plan.daily_journal_limit if plan else 0
        ),
        analyze_today=_bucket(
            analyze_used, plan.daily_analyze_limit if plan else 0
        ),
        weekly_summaries_this_week=_bucket(
            summary_used, plan.weekly_summary_limit if plan else 0
        ),
        insights_this_week=_bucket(
            insights_used, plan.weekly_insights_limit if plan else 0
        ),
    )


def _limit_for_action(plan: SubscriptionPlan | None, action: str) -> int | None:
    if plan is None:
        return 0
    mapping = {
        ACTION_JOURNAL: plan.daily_journal_limit,
        ACTION_ANALYZE: plan.daily_analyze_limit,
        ACTION_WEEKLY_SUMMARY: plan.weekly_summary_limit,
        ACTION_INSIGHTS: plan.weekly_insights_limit,
    }
    return mapping[action]


def _used_for_action(db: Session, user_id: int, action: str) -> int:
    if action == ACTION_JOURNAL:
        return _count_journals_today(db, user_id)
    if action == ACTION_ANALYZE:
        start, end = _day_bounds()
        return _count_usage_events(db, user_id, action, start, end)
    start, end = _week_bounds()
    return _count_usage_events(db, user_id, action, start, end)


def require_quota(db: Session, user_id: int, action: str) -> None:
    plan = get_user_plan(db, user_id)
    if plan is None:
        user = db.get(User, user_id)
        if user is None:
            raise NotFoundError("User not found")
        sub = get_user_subscription(db, user_id)
        if sub is None:
            # First-time user: grant default Free trial window.
            assign_default_plan(db, user, commit=True)
            plan = get_user_plan(db, user_id)
        else:
            # Expired / canceled — do not auto-regrant Free forever.
            raise BadRequestError(
                "Your plan has expired. Open Plans to renew or choose a membership."
            )

    if plan is None:
        raise BadRequestError(
            "Your plan has expired. Open Plans to renew or choose a membership."
        )

    limit = _limit_for_action(plan, action)
    if limit is None:
        return

    used = _used_for_action(db, user_id, action)
    if used >= limit:
        plan_name = plan.name if plan else "Free"
        label = _ACTION_LABELS.get(action, action)
        retry = (
            "tomorrow"
            if action in (ACTION_JOURNAL, ACTION_ANALYZE)
            else "next week"
        )
        raise BadRequestError(
            f"{label} limit reached ({used}/{limit} on {plan_name}). "
            f"Upgrade or try again {retry}."
        )


def record_usage(db: Session, user_id: int, action: str, *, commit: bool = True) -> UsageEvent:
    event = UsageEvent(user_id=user_id, action=action)
    db.add(event)
    if commit:
        db.commit()
        db.refresh(event)
    else:
        db.flush()
    return event


def resolve_plan_features(plan: SubscriptionPlan) -> list[str]:
    raw = plan.features
    if isinstance(raw, str):
        import json

        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            raw = None
    if isinstance(raw, list) and any(str(x).strip() for x in raw):
        return [str(x).strip() for x in raw if str(x).strip()]

    def line(limit: int | None, unlimited: str, capped: str) -> str:
        return unlimited if limit is None else capped.format(n=limit)

    return [
        line(plan.daily_journal_limit, "Unlimited journal entries", "{n} journal entries per day"),
        line(plan.daily_analyze_limit, "Unlimited AI sentiment analysis", "{n} AI analyses per day"),
        line(
            plan.weekly_summary_limit,
            "Unlimited weekly summaries",
            "{n} weekly summary per week",
        ),
        line(plan.weekly_insights_limit, "Unlimited insights", "{n} insights generation per week"),
        "Mood trends & Excel export",
        "Achievements & streaks",
    ]


def to_plan_summary(plan: SubscriptionPlan | None) -> PlanSummary | None:
    if plan is None:
        return None
    data = PlanSummary.model_validate(plan)
    return data.model_copy(update={"features": resolve_plan_features(plan)})
