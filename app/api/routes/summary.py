"""Weekly summary endpoints: generate and read AI digests scoped to the user."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.summary import WeeklySummaryGenerate, WeeklySummaryRead
from app.services import summary_service

router = APIRouter(prefix="/summary", tags=["summary"])


@router.post(
    "/weekly",
    response_model=WeeklySummaryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Generate (or regenerate) a weekly AI summary",
)
def generate_weekly_summary(
    payload: WeeklySummaryGenerate | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WeeklySummaryRead:
    """Summarize the week's entries. Omit the body (or `week_of`) for the current week.

    Returns `400` if the week has no entries, `502` if the AI provider is unavailable.
    """
    week_of = payload.week_of if payload else None
    return summary_service.generate_weekly_summary(db, current_user.id, week_of)


@router.get(
    "/weekly",
    response_model=list[WeeklySummaryRead],
    summary="List weekly summaries (newest first)",
)
def list_weekly_summaries(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[WeeklySummaryRead]:
    return summary_service.list_weekly_summaries(db, current_user.id)


@router.get(
    "/weekly/{summary_id}",
    response_model=WeeklySummaryRead,
    summary="Get one weekly summary",
)
def get_weekly_summary(
    summary_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WeeklySummaryRead:
    return summary_service.get_weekly_summary(db, current_user.id, summary_id)
