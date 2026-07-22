"""Analytics endpoints: owner-scoped dashboards and trend aggregations."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.analytics import (
    DashboardAnalytics,
    MonthlyAnalytics,
    MoodDistribution,
    YearlyAnalytics,
)
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard", response_model=DashboardAnalytics, summary="Overview stats + streaks")
def dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardAnalytics:
    return analytics_service.get_dashboard(db, current_user.id)


@router.get(
    "/mood-distribution",
    response_model=MoodDistribution,
    summary="Sentiment / emotion / mood distribution",
)
def mood_distribution(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MoodDistribution:
    return analytics_service.get_mood_distribution(db, current_user.id)


@router.get("/monthly", response_model=MonthlyAnalytics, summary="Per-month stats for a year")
def monthly(
    year: int | None = Query(default=None, ge=1970, le=9999, description="Defaults to the current year"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MonthlyAnalytics:
    return analytics_service.get_monthly(db, current_user.id, year)


@router.get("/yearly", response_model=YearlyAnalytics, summary="Per-year stats across all history")
def yearly(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> YearlyAnalytics:
    return analytics_service.get_yearly(db, current_user.id)
