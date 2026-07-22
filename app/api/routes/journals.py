"""Journal endpoints: CRUD scoped to the authenticated user, with pagination/sort/search."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.pagination import PaginationParams, get_pagination
from app.models.user import User
from app.schemas.journal import JournalCreate, JournalListResponse, JournalRead, JournalUpdate
from app.schemas.sentiment import SentimentRead
from app.services import journal_service, sentiment_service

router = APIRouter(prefix="/journals", tags=["journals"])


@router.post(
    "",
    response_model=JournalRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a journal entry",
)
def create_journal(
    payload: JournalCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JournalRead:
    return journal_service.create_journal(db, current_user.id, payload)


@router.get(
    "",
    response_model=JournalListResponse,
    summary="List journal entries (paginated, sortable, searchable)",
)
def list_journals(
    pagination: PaginationParams = Depends(get_pagination),
    sort_by: Literal["created_at", "updated_at", "title"] = Query("created_at"),
    order: Literal["asc", "desc"] = Query("desc"),
    q: str | None = Query(default=None, max_length=200, description="Keyword search over title/content"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JournalListResponse:
    items, total = journal_service.list_journals(db, current_user.id, pagination, sort_by, order, q)
    total_pages = (total + pagination.page_size - 1) // pagination.page_size if total else 0
    return JournalListResponse(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=total_pages,
    )


@router.get("/{journal_id}", response_model=JournalRead, summary="Get a journal entry")
def get_journal(
    journal_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JournalRead:
    return journal_service.get_journal(db, current_user.id, journal_id)


@router.put("/{journal_id}", response_model=JournalRead, summary="Update a journal entry")
def update_journal(
    journal_id: int,
    payload: JournalUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JournalRead:
    entry = journal_service.get_journal(db, current_user.id, journal_id)
    return journal_service.update_journal(db, entry, payload)


@router.delete(
    "/{journal_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a journal entry",
)
def delete_journal(
    journal_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    entry = journal_service.get_journal(db, current_user.id, journal_id)
    journal_service.delete_journal(db, entry)


@router.post(
    "/{journal_id}/analyze",
    response_model=SentimentRead,
    summary="Analyze a journal entry's sentiment via AI",
)
def analyze_journal(
    journal_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SentimentRead:
    """Run AI sentiment analysis on the entry and store the result.

    Re-running overwrites the previous analysis. Returns `502` if the AI
    provider is unavailable or returns a malformed response.
    """
    return sentiment_service.analyze_journal(db, current_user.id, journal_id)


@router.get(
    "/{journal_id}/sentiment",
    response_model=SentimentRead,
    summary="Get the stored sentiment for a journal entry",
)
def get_journal_sentiment(
    journal_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SentimentRead:
    """Return the stored analysis, or `404` if the entry hasn't been analyzed yet."""
    return sentiment_service.get_sentiment(db, current_user.id, journal_id)
