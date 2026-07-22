"""Insights endpoints: generate and list AI observations, scoped to the user."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.pagination import PaginationParams, get_pagination
from app.models.user import User
from app.schemas.insight import InsightListResponse, InsightRead
from app.services import insight_service

router = APIRouter(prefix="/insights", tags=["insights"])


@router.post(
    "/generate",
    response_model=list[InsightRead],
    status_code=status.HTTP_201_CREATED,
    summary="Generate and store a fresh batch of AI insights",
)
def generate_insights(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[InsightRead]:
    """Analyze the user's history and store new insights.

    Returns `400` if there are no entries yet, `502` if the AI provider is unavailable.
    """
    return insight_service.generate_insights(db, current_user.id)


@router.get(
    "",
    response_model=InsightListResponse,
    summary="List stored insights (newest first, paginated)",
)
def list_insights(
    pagination: PaginationParams = Depends(get_pagination),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InsightListResponse:
    items, total = insight_service.list_insights(db, current_user.id, pagination)
    total_pages = (total + pagination.page_size - 1) // pagination.page_size if total else 0
    return InsightListResponse(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=total_pages,
    )
