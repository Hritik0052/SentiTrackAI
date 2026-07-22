"""Search business logic: owner-scoped journal search across keyword, date range,
and sentiment attributes (mood / emotion / sentiment value), paginated and sortable.

Filtering on any sentiment attribute joins `sentiments`, which naturally excludes
entries that haven't been analyzed. Keyword/date-only searches keep all entries and
return the nested sentiment where present.
"""

from __future__ import annotations

from datetime import date, datetime, time

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import BadRequestError
from app.models.journal_entry import JournalEntry
from app.models.sentiment import Sentiment

SORTABLE_FIELDS = {
    "created_at": JournalEntry.created_at,
    "updated_at": JournalEntry.updated_at,
    "title": JournalEntry.title,
}


def search_journals(
    db: Session,
    user_id: int,
    *,
    q: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    mood: str | None = None,
    emotion: str | None = None,
    sentiment: str | None = None,
    page: int,
    page_size: int,
    sort_by: str = "created_at",
    order: str = "desc",
) -> tuple[list[JournalEntry], int]:
    if date_from and date_to and date_from > date_to:
        raise BadRequestError("date_from must be on or before date_to")

    conditions = []
    if q:
        pattern = f"%{q}%"
        conditions.append(or_(JournalEntry.title.ilike(pattern), JournalEntry.content.ilike(pattern)))
    if date_from:
        conditions.append(JournalEntry.created_at >= datetime.combine(date_from, time.min))
    if date_to:
        conditions.append(JournalEntry.created_at <= datetime.combine(date_to, time.max))
    if mood:
        conditions.append(func.lower(Sentiment.mood) == mood.lower())
    if emotion:
        conditions.append(func.lower(Sentiment.emotion) == emotion.lower())
    if sentiment:
        conditions.append(Sentiment.sentiment == sentiment.lower())

    needs_sentiment_join = any((mood, emotion, sentiment))

    stmt = select(JournalEntry).where(JournalEntry.user_id == user_id)
    count_stmt = select(func.count()).select_from(JournalEntry).where(JournalEntry.user_id == user_id)
    if needs_sentiment_join:
        stmt = stmt.join(Sentiment, Sentiment.journal_id == JournalEntry.id)
        count_stmt = count_stmt.join(Sentiment, Sentiment.journal_id == JournalEntry.id)
    for condition in conditions:
        stmt = stmt.where(condition)
        count_stmt = count_stmt.where(condition)

    sort_column = SORTABLE_FIELDS.get(sort_by, JournalEntry.created_at)
    stmt = stmt.order_by(sort_column.asc() if order == "asc" else sort_column.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    # Eager-load the nested sentiment so serializing results doesn't fire N+1 queries.
    stmt = stmt.options(selectinload(JournalEntry.sentiment))

    items = list(db.scalars(stmt).all())
    total = db.scalar(count_stmt) or 0
    return items, total
