"""Search endpoint: owner-scoped journal search with keyword/date/mood/emotion filters."""

from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.pagination import PaginationParams, get_pagination
from app.models.user import User
from app.schemas.search import SearchResponse
from app.services import search_service

router = APIRouter(prefix="/search", tags=["search"])


@router.get(
    "",
    response_model=SearchResponse,
    summary="Search journal entries by keyword, date range, mood, emotion, or sentiment",
)
def search(
    q: str | None = Query(default=None, max_length=200, description="Keyword over title/content"),
    date_from: date | None = Query(default=None, description="Inclusive start date (created_at)"),
    date_to: date | None = Query(default=None, description="Inclusive end date (created_at)"),
    mood: str | None = Query(default=None, max_length=50, description="Exact mood match (case-insensitive)"),
    emotion: str | None = Query(default=None, max_length=50, description="Exact emotion match (case-insensitive)"),
    sentiment: Literal["positive", "neutral", "negative"] | None = Query(default=None),
    sort_by: Literal["created_at", "updated_at", "title"] = Query("created_at"),
    order: Literal["asc", "desc"] = Query("desc"),
    pagination: PaginationParams = Depends(get_pagination),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SearchResponse:
    items, total = search_service.search_journals(
        db,
        current_user.id,
        q=q,
        date_from=date_from,
        date_to=date_to,
        mood=mood,
        emotion=emotion,
        sentiment=sentiment,
        page=pagination.page,
        page_size=pagination.page_size,
        sort_by=sort_by,
        order=order,
    )
    total_pages = (total + pagination.page_size - 1) // pagination.page_size if total else 0
    return SearchResponse(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=total_pages,
    )
