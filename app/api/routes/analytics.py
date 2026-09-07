"""Analytics endpoints: owner-scoped dashboards and trend aggregations."""

from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.analytics import (
    DashboardAnalytics,
    MonthlyAnalytics,
    MoodDistribution,
    MoodTrends,
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


@router.get(
    "/mood-trends",
    response_model=MoodTrends,
    summary="Daily multi-line mood/emotion trends for a week or month",
)
def mood_trends(
    period: Literal["week", "month"] = Query(default="week"),
    anchor: date | None = Query(
        default=None,
        description="Any date inside the target week/month (defaults to today)",
    ),
    top_emotions: int = Query(default=5, ge=1, le=8),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MoodTrends:
    return analytics_service.get_mood_trends(
        db,
        current_user.id,
        period=period,
        anchor=anchor,
        top_emotions=top_emotions,
    )


@router.get(
    "/mood-trends/compare",
    response_model=MoodTrends,
    summary="Daily mood/emotion trends for a custom date range (max 90 days)",
)
def mood_trends_compare(
    date_from: date = Query(alias="from", description="Inclusive start date"),
    date_to: date = Query(alias="to", description="Inclusive end date"),
    top_emotions: int = Query(default=5, ge=1, le=8),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MoodTrends:
    return analytics_service.get_mood_trends_compare(
        db,
        current_user.id,
        date_from=date_from,
        date_to=date_to,
        top_emotions=top_emotions,
    )
