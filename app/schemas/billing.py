"""Billing / plan / usage schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PlanSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: str | None = None
    daily_journal_limit: int | None = None
    weekly_summary_limit: int | None = None
    daily_analyze_limit: int | None = None
    weekly_insights_limit: int | None = None
    is_default: bool = False
    is_active: bool = True
    sort_order: int = 0
    price_inr: int | None = None
    billing_period: str | None = None


class QuotaBucket(BaseModel):
    used: int
    limit: int | None = None
    remaining: int | None = None


class UsageSnapshot(BaseModel):
    plan: PlanSummary | None = None
    journals_today: QuotaBucket
    analyze_today: QuotaBucket
    weekly_summaries_this_week: QuotaBucket
    insights_this_week: QuotaBucket


class PlanCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    daily_journal_limit: int | None = Field(default=None, ge=0)
    weekly_summary_limit: int | None = Field(default=None, ge=0)
    daily_analyze_limit: int | None = Field(default=None, ge=0)
    weekly_insights_limit: int | None = Field(default=None, ge=0)
    is_active: bool = True
    sort_order: int = 0
    price_inr: int | None = Field(default=None, ge=0)
    billing_period: str | None = Field(default=None, max_length=32)
    cashfree_plan_id: str | None = Field(default=None, max_length=128)


class PlanUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    daily_journal_limit: int | None = Field(default=None, ge=0)
    weekly_summary_limit: int | None = Field(default=None, ge=0)
    daily_analyze_limit: int | None = Field(default=None, ge=0)
    weekly_insights_limit: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
    sort_order: int | None = None
    price_inr: int | None = Field(default=None, ge=0)
    billing_period: str | None = Field(default=None, max_length=32)
    cashfree_plan_id: str | None = Field(default=None, max_length=128)


class AdminUserUpdate(BaseModel):
    plan_id: int | None = None
    is_admin: bool | None = None
    notes: str | None = None
    status: str | None = Field(default=None, pattern="^(active|canceled)$")


class AdminUserListItem(BaseModel):
    id: int
    name: str
    email: str
    is_admin: bool
    created_at: datetime
    plan: PlanSummary | None = None
    subscription_status: str | None = None


class AdminUserDetail(AdminUserListItem):
    notes: str | None = None
    usage: UsageSnapshot | None = None


class AdminStats(BaseModel):
    total_users: int
    admin_users: int
    journals_today: int
    analyze_today: int
    weekly_summaries_today: int
    insights_today: int
    plan_counts: dict[str, int]
