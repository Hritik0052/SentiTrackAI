"""Journal business logic: owner-scoped CRUD, pagination, sorting, keyword search."""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.dependencies.pagination import PaginationParams
from app.models.journal_entry import JournalEntry
from app.schemas.journal import JournalCreate, JournalUpdate

SORTABLE_FIELDS = {
    "created_at": JournalEntry.created_at,
    "updated_at": JournalEntry.updated_at,
    "title": JournalEntry.title,
}


def create_journal(db: Session, user_id: int, payload: JournalCreate) -> JournalEntry:
    entry = JournalEntry(user_id=user_id, title=payload.title, content=payload.content)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_journal(db: Session, user_id: int, journal_id: int) -> JournalEntry:
    entry = db.get(JournalEntry, journal_id)
    if entry is None or entry.user_id != user_id:
        raise NotFoundError("Journal entry not found")
    return entry


def list_journals(
    db: Session,
    user_id: int,
    pagination: PaginationParams,
    sort_by: str = "created_at",
    order: str = "desc",
    q: str | None = None,
) -> tuple[list[JournalEntry], int]:
    stmt = select(JournalEntry).where(JournalEntry.user_id == user_id)
    count_stmt = select(func.count()).select_from(JournalEntry).where(JournalEntry.user_id == user_id)

    if q:
        pattern = f"%{q}%"
        keyword_filter = or_(JournalEntry.title.ilike(pattern), JournalEntry.content.ilike(pattern))
        stmt = stmt.where(keyword_filter)
        count_stmt = count_stmt.where(keyword_filter)

    sort_column = SORTABLE_FIELDS.get(sort_by, JournalEntry.created_at)
    stmt = stmt.order_by(sort_column.asc() if order == "asc" else sort_column.desc())
    stmt = stmt.offset(pagination.offset).limit(pagination.limit)

    items = list(db.scalars(stmt).all())
    total = db.scalar(count_stmt) or 0
    return items, total


def update_journal(db: Session, entry: JournalEntry, payload: JournalUpdate) -> JournalEntry:
    data = payload.model_dump(exclude_unset=True)
    if "title" in data:
        entry.title = data["title"]
    if "content" in data:
        entry.content = data["content"]
    db.commit()
    db.refresh(entry)
    return entry


def delete_journal(db: Session, entry: JournalEntry) -> None:
    db.delete(entry)
    db.commit()
