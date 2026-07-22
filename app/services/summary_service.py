"""Weekly summary business logic.

Gathers a user's journal entries for a Monday–Sunday week, runs them through the
AI weekly-digest prompt, and upserts one ``weekly_summaries`` row per (user, week).
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, NotFoundError
from app.models.journal_entry import JournalEntry
from app.models.weekly_summary import WeeklySummary
from app.services import ai_service


def _week_bounds(day: date) -> tuple[date, date]:
    """Return the Monday (start) and Sunday (end) of the week containing ``day``."""
    start = day - timedelta(days=day.weekday())
    return start, start + timedelta(days=6)


def generate_weekly_summary(
    db: Session, user_id: int, week_of: date | None = None
) -> WeeklySummary:
    """Generate (or regenerate) the weekly summary for the week containing ``week_of``.

    Defaults to the current week. Raises ``BadRequestError`` if the week has no
    entries, and ``AIServiceError`` (502) if the AI provider fails.
    """
    week_start, week_end = _week_bounds(week_of or date.today())

    # Compare against a datetime range rather than casting created_at to a DATE:
    # SQLite has no real DATE type, so CAST(... AS DATE) would mis-parse the timestamp.
    start_dt = datetime.combine(week_start, time.min)
    end_dt = datetime.combine(week_end, time.max)
    entries = list(
        db.scalars(
            select(JournalEntry)
            .where(
                JournalEntry.user_id == user_id,
                JournalEntry.created_at >= start_dt,
                JournalEntry.created_at <= end_dt,
            )
            .order_by(JournalEntry.created_at.asc())
        ).all()
    )
    if not entries:
        raise BadRequestError("No journal entries in this week to summarize")

    result = ai_service.generate_weekly_summary([entry.content for entry in entries])

    record = db.scalar(
        select(WeeklySummary).where(
            WeeklySummary.user_id == user_id,
            WeeklySummary.week_start == week_start,
        )
    )
    if record is None:
        record = WeeklySummary(user_id=user_id, week_start=week_start)
        db.add(record)

    record.week_end = week_end
    record.summary = result["summary"]
    record.suggestions = result["suggestions"]
    record.entry_count = len(entries)

    db.commit()
    db.refresh(record)
    return record


def list_weekly_summaries(db: Session, user_id: int) -> list[WeeklySummary]:
    """Return the user's weekly summaries, most recent week first."""
    return list(
        db.scalars(
            select(WeeklySummary)
            .where(WeeklySummary.user_id == user_id)
            .order_by(WeeklySummary.week_start.desc())
        ).all()
    )


def get_weekly_summary(db: Session, user_id: int, summary_id: int) -> WeeklySummary:
    """Return one owned weekly summary, or 404 if missing / not owned."""
    record = db.get(WeeklySummary, summary_id)
    if record is None or record.user_id != user_id:
        raise NotFoundError("Weekly summary not found")
    return record
