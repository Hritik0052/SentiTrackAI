"""Admin API: plans, users, stats."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_admin
from app.dependencies.pagination import PaginationParams, get_pagination
from app.models.user import User
from app.schemas.billing import (
    AdminStats,
    AdminUserDetail,
    AdminUserListItem,
    AdminUserUpdate,
    PlanCreate,
    PlanSummary,
    PlanUpdate,
)
from app.services import admin_service, billing_service

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats", response_model=AdminStats, summary="Admin overview KPIs")
def admin_stats(
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> AdminStats:
    return admin_service.get_stats(db)


@router.get("/plans", response_model=list[PlanSummary], summary="List subscription plans")
def list_plans(
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> list[PlanSummary]:
    return [billing_service.to_plan_summary(p) for p in billing_service.list_plans(db)]  # type: ignore[misc]


@router.post(
    "/plans",
    response_model=PlanSummary,
    status_code=status.HTTP_201_CREATED,
    summary="Create a subscription plan",
)
def create_plan(
    payload: PlanCreate,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> PlanSummary:
    plan = billing_service.create_plan(db, payload)
    return billing_service.to_plan_summary(plan)  # type: ignore[return-value]


@router.get("/plans/{plan_id}", response_model=PlanSummary, summary="Get a plan")
def get_plan(
    plan_id: int,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> PlanSummary:
    return billing_service.to_plan_summary(billing_service.get_plan(db, plan_id))  # type: ignore[return-value]


@router.patch("/plans/{plan_id}", response_model=PlanSummary, summary="Update a plan")
def patch_plan(
    plan_id: int,
    payload: PlanUpdate,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> PlanSummary:
    plan = billing_service.get_plan(db, plan_id)
    updated = billing_service.update_plan(db, plan, payload)
    return billing_service.to_plan_summary(updated)  # type: ignore[return-value]


@router.post(
    "/plans/{plan_id}/set-default",
    response_model=PlanSummary,
    summary="Make this the default plan for new users",
)
def set_default_plan(
    plan_id: int,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> PlanSummary:
    plan = billing_service.get_plan(db, plan_id)
    updated = billing_service.set_default_plan(db, plan)
    return billing_service.to_plan_summary(updated)  # type: ignore[return-value]


@router.get("/users", summary="List users")
def list_users(
    q: str | None = Query(default=None, description="Search by email or name"),
    pagination: PaginationParams = Depends(get_pagination),
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict:
    items, total = admin_service.list_users(db, pagination, q=q)
    return {
        "items": [AdminUserListItem.model_validate(i) for i in items],
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
    }


@router.get("/users/{user_id}", response_model=AdminUserDetail, summary="User detail + usage")
def get_user(
    user_id: int,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> AdminUserDetail:
    return admin_service.get_user_detail(db, user_id)


@router.patch("/users/{user_id}", response_model=AdminUserDetail, summary="Update user admin/plan")
def patch_user(
    user_id: int,
    payload: AdminUserUpdate,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> AdminUserDetail:
    return admin_service.update_user(db, user_id, payload)
