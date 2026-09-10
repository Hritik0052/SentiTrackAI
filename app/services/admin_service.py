"""Admin dashboard queries: stats, users list/detail, patch user."""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import NotFoundError
from app.dependencies.pagination import PaginationParams
from app.models.journal_entry import JournalEntry
from app.models.subscription_plan import SubscriptionPlan
from app.models.usage_event import UsageEvent
from app.models.user import User
from app.models.user_subscription import UserSubscription
from app.schemas.billing import (
    AdminStats,
    AdminUserDetail,
    AdminUserListItem,
    AdminUserUpdate,
    PlanSummary,
)
from app.services import billing_service


def get_stats(db: Session) -> AdminStats:
    total_users = db.scalar(select(func.count()).select_from(User)) or 0
    admin_users = (
        db.scalar(select(func.count()).select_from(User).where(User.is_admin.is_(True))) or 0
    )

    day_start, day_end = billing_service._day_bounds()
    journals_today = (
        db.scalar(
            select(func.count())
            .select_from(JournalEntry)
            .where(
                JournalEntry.created_at >= day_start,
                JournalEntry.created_at <= day_end,
            )
        )
        or 0
    )

    def _events_today(action: str) -> int:
        return (
            db.scalar(
                select(func.count())
                .select_from(UsageEvent)
                .where(
                    UsageEvent.action == action,
                    UsageEvent.created_at >= day_start,
                    UsageEvent.created_at <= day_end,
                )
            )
            or 0
        )

    plan_rows = db.execute(
        select(SubscriptionPlan.code, func.count(UserSubscription.id))
        .select_from(SubscriptionPlan)
        .outerjoin(
            UserSubscription,
            (UserSubscription.plan_id == SubscriptionPlan.id)
            & (UserSubscription.status == "active"),
        )
        .group_by(SubscriptionPlan.code)
    ).all()
    plan_counts = {code: count for code, count in plan_rows}

    return AdminStats(
        total_users=total_users,
        admin_users=admin_users,
        journals_today=journals_today,
        analyze_today=_events_today(billing_service.ACTION_ANALYZE),
        weekly_summaries_today=_events_today(billing_service.ACTION_WEEKLY_SUMMARY),
        insights_today=_events_today(billing_service.ACTION_INSIGHTS),
        plan_counts=plan_counts,
    )


def _to_list_item(user: User) -> AdminUserListItem:
    sub = user.subscription
    plan = sub.plan if sub is not None else None
    return AdminUserListItem(
        id=user.id,
        name=user.name,
        email=user.email,
        is_admin=user.is_admin,
        created_at=user.created_at,
        plan=billing_service.to_plan_summary(plan) if plan else None,
        subscription_status=sub.status if sub else None,
    )


def list_users(
    db: Session,
    pagination: PaginationParams,
    *,
    q: str | None = None,
) -> tuple[list[AdminUserListItem], int]:
    stmt = (
        select(User)
        .options(joinedload(User.subscription).joinedload(UserSubscription.plan))
        .order_by(User.created_at.desc())
    )
    count_stmt = select(func.count()).select_from(User)

    if q:
        pattern = f"%{q}%"
        filt = or_(User.email.ilike(pattern), User.name.ilike(pattern))
        stmt = stmt.where(filt)
        count_stmt = count_stmt.where(filt)

    total = db.scalar(count_stmt) or 0
    users = list(
        db.scalars(stmt.offset(pagination.offset).limit(pagination.limit)).unique().all()
    )
    return [_to_list_item(u) for u in users], total


def get_user_detail(db: Session, user_id: int) -> AdminUserDetail:
    user = db.scalar(
        select(User)
        .options(joinedload(User.subscription).joinedload(UserSubscription.plan))
        .where(User.id == user_id)
    )
    if user is None:
        raise NotFoundError("User not found")
    base = _to_list_item(user)
    notes = user.subscription.notes if user.subscription else None
    return AdminUserDetail(
        **base.model_dump(),
        notes=notes,
        usage=billing_service.get_usage_snapshot(db, user.id),
    )


def update_user(db: Session, user_id: int, payload: AdminUserUpdate) -> AdminUserDetail:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found")

    data = payload.model_dump(exclude_unset=True)

    if "is_admin" in data and data["is_admin"] is not None:
        user.is_admin = data["is_admin"]

    plan = None
    if "plan_id" in data and data["plan_id"] is not None:
        plan = billing_service.get_plan(db, data["plan_id"])

    notes = data.get("notes") if "notes" in data else None
    status = data.get("status") if "status" in data else None

    if plan is not None or notes is not None or status is not None:
        if plan is None:
            sub = billing_service.get_user_subscription(db, user.id)
            if sub is None:
                billing_service.assign_default_plan(db, user, commit=False)
                sub = billing_service.get_user_subscription(db, user.id)
            plan = sub.plan if sub else billing_service.get_default_plan(db)
        billing_service.assign_plan(
            db,
            user,
            plan,
            notes=notes if "notes" in data else None,
            status=status or "active",
            commit=False,
        )

    db.commit()
    return get_user_detail(db, user.id)
