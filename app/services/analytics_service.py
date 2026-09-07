"""Analytics business logic.

Every endpoint aggregates the same owner-scoped dataset: each journal entry joined
to its sentiment (if analyzed). Aggregation is done in Python rather than with
backend-specific date/SQL functions, keeping the code portable across SQLite and
PostgreSQL — per-user volumes are small enough that this is not a concern.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError
from app.models.journal_entry import JournalEntry
from app.models.sentiment import Sentiment

_SENTIMENT_KEYS = ("positive", "neutral", "negative")


class _Row:
    """Lightweight view of one entry + its (optional) sentiment."""

    __slots__ = ("created_at", "sentiment", "emotion", "mood", "confidence")

    def __init__(self, created_at, sentiment, emotion, mood, confidence):
        self.created_at: datetime = created_at
        self.sentiment: str | None = sentiment
        self.emotion: str | None = emotion
        self.mood: str | None = mood
        self.confidence: float | None = confidence


def _load_rows(db: Session, user_id: int) -> list[_Row]:
    result = db.execute(
        select(
            JournalEntry.created_at,
            Sentiment.sentiment,
            Sentiment.emotion,
            Sentiment.mood,
            Sentiment.confidence,
        )
        .outerjoin(Sentiment, Sentiment.journal_id == JournalEntry.id)
        .where(JournalEntry.user_id == user_id)
        .order_by(JournalEntry.created_at.asc())
    ).all()
    return [_Row(*r) for r in result]


def _sentiment_counts(rows: list[_Row]) -> dict[str, int]:
    counter = Counter(r.sentiment for r in rows if r.sentiment)
    return {key: counter.get(key, 0) for key in _SENTIMENT_KEYS}


def _average_confidence(rows: list[_Row]) -> float | None:
    values = [r.confidence for r in rows if r.confidence is not None]
    return round(sum(values) / len(values), 4) if values else None


def _most_common(values) -> str | None:
    counter = Counter(v for v in values if v)
    return counter.most_common(1)[0][0] if counter else None


def _week_bounds(day: date) -> tuple[date, date]:
    start = day - timedelta(days=day.weekday())
    return start, start + timedelta(days=6)


def _compute_streaks(dates: list[date]) -> tuple[int, int]:
    """Return (current_streak, longest_streak) over sorted unique entry dates."""
    if not dates:
        return 0, 0

    longest = run = 1
    for prev, cur in zip(dates, dates[1:]):
        run = run + 1 if (cur - prev).days == 1 else 1
        longest = max(longest, run)

    # Trailing run ending at the most recent entry date.
    trailing = 1
    for i in range(len(dates) - 1, 0, -1):
        if (dates[i] - dates[i - 1]).days == 1:
            trailing += 1
        else:
            break

    # Only "current" if the last entry was today or yesterday.
    current = trailing if (date.today() - dates[-1]).days <= 1 else 0
    return current, longest


def _period_stat(period: str, rows: list[_Row]) -> dict:
    sentiments = [r.sentiment for r in rows if r.sentiment]
    return {
        "period": period,
        "entries": len(rows),
        "analyzed": len(sentiments),
        "sentiment_counts": _sentiment_counts(rows),
        "average_confidence": _average_confidence(rows),
        "most_common_emotion": _most_common(r.emotion for r in rows),
    }


def get_dashboard(db: Session, user_id: int) -> dict:
    rows = _load_rows(db, user_id)

    unique_dates = sorted({r.created_at.date() for r in rows})
    current_streak, longest_streak = _compute_streaks(unique_dates)

    today = date.today()
    week_start, week_end = _week_bounds(today)
    entries_this_week = sum(1 for r in rows if week_start <= r.created_at.date() <= week_end)
    entries_this_month = sum(
        1 for r in rows if r.created_at.year == today.year and r.created_at.month == today.month
    )

    return {
        "total_entries": len(rows),
        "analyzed_entries": sum(1 for r in rows if r.sentiment),
        "sentiment_counts": _sentiment_counts(rows),
        "average_confidence": _average_confidence(rows),
        "most_common_emotion": _most_common(r.emotion for r in rows),
        "most_common_mood": _most_common(r.mood for r in rows),
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "entries_this_week": entries_this_week,
        "entries_this_month": entries_this_month,
        "first_entry_at": rows[0].created_at if rows else None,
        "last_entry_at": rows[-1].created_at if rows else None,
    }


def get_mood_distribution(db: Session, user_id: int) -> dict:
    rows = _load_rows(db, user_id)
    emotion_counts = Counter(r.emotion for r in rows if r.emotion)
    mood_counts = Counter(r.mood for r in rows if r.mood)
    return {
        "total_analyzed": sum(1 for r in rows if r.sentiment),
        "sentiment_counts": _sentiment_counts(rows),
        "emotions": [
            {"label": label, "count": count} for label, count in emotion_counts.most_common()
        ],
        "moods": [
            {"label": label, "count": count} for label, count in mood_counts.most_common()
        ],
    }


def get_monthly(db: Session, user_id: int, year: int | None = None) -> dict:
    target_year = year or date.today().year
    rows = [r for r in _load_rows(db, user_id) if r.created_at.year == target_year]

    buckets: dict[str, list[_Row]] = defaultdict(list)
    for row in rows:
        buckets[f"{target_year:04d}-{row.created_at.month:02d}"].append(row)

    months = [_period_stat(period, buckets[period]) for period in sorted(buckets)]
    return {"year": target_year, "months": months}


def get_yearly(db: Session, user_id: int) -> dict:
    rows = _load_rows(db, user_id)

    buckets: dict[str, list[_Row]] = defaultdict(list)
    for row in rows:
        buckets[f"{row.created_at.year:04d}"].append(row)

    years = [_period_stat(period, buckets[period]) for period in sorted(buckets)]
    return {"years": years}


def _normalize_emotion(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().lower()
    return normalized or None


def _month_bounds(day: date) -> tuple[date, date]:
    start = day.replace(day=1)
    if start.month == 12:
        end = date(start.year, 12, 31)
    else:
        end = date(start.year, start.month + 1, 1) - timedelta(days=1)
    return start, end


def _daterange(start: date, end: date) -> list[date]:
    days = (end - start).days
    return [start + timedelta(days=offset) for offset in range(days + 1)]


def _build_mood_trends(
    rows: list[_Row],
    *,
    period: str,
    start: date,
    end: date,
    top_emotions: int,
) -> dict:
    in_range = [r for r in rows if start <= r.created_at.date() <= end]
    analyzed = [r for r in in_range if r.sentiment]

    emotion_counter: Counter[str] = Counter()
    for row in analyzed:
        emotion = _normalize_emotion(row.emotion)
        if emotion:
            emotion_counter[emotion] += 1

    emotion_series = [label for label, _ in emotion_counter.most_common(top_emotions)]

    by_day: dict[date, list[_Row]] = defaultdict(list)
    for row in analyzed:
        by_day[row.created_at.date()].append(row)

    buckets: list[dict] = []
    for day in _daterange(start, end):
        day_rows = by_day.get(day, [])
        day_emotions: dict[str, int] = {label: 0 for label in emotion_series}
        for row in day_rows:
            emotion = _normalize_emotion(row.emotion)
            if emotion in day_emotions:
                day_emotions[emotion] += 1
        buckets.append(
            {
                "date": day,
                "sentiment": _sentiment_counts(day_rows),
                "emotions": day_emotions,
            }
        )

    return {
        "period": period,
        "start": start,
        "end": end,
        "granularity": "day",
        "buckets": buckets,
        "series": {
            "sentiment": list(_SENTIMENT_KEYS),
            "emotions": emotion_series,
        },
        "totals": {
            "entries": len(in_range),
            "analyzed": len(analyzed),
            "sentiment_counts": _sentiment_counts(analyzed),
            "emotion_counts": {label: emotion_counter.get(label, 0) for label in emotion_series},
        },
    }


def get_mood_trends(
    db: Session,
    user_id: int,
    *,
    period: str = "week",
    anchor: date | None = None,
    top_emotions: int = 5,
) -> dict:
    day = anchor or date.today()
    if period == "week":
        start, end = _week_bounds(day)
    elif period == "month":
        start, end = _month_bounds(day)
    else:
        raise BadRequestError("period must be 'week' or 'month'")

    return _build_mood_trends(
        _load_rows(db, user_id),
        period=period,
        start=start,
        end=end,
        top_emotions=top_emotions,
    )


def get_mood_trends_compare(
    db: Session,
    user_id: int,
    *,
    date_from: date,
    date_to: date,
    top_emotions: int = 5,
) -> dict:
    if date_from > date_to:
        raise BadRequestError("from must be on or before to")
    if (date_to - date_from).days > 90:
        raise BadRequestError("Custom mood-trend range cannot exceed 90 days")

    return _build_mood_trends(
        _load_rows(db, user_id),
        period="custom",
        start=date_from,
        end=date_to,
        top_emotions=top_emotions,
    )
