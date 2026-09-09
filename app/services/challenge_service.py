"""Weekly challenges: ensure active set, update progress, award XP on complete."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.gamification.challenge_catalog import CHALLENGE_BY_KEY, CHALLENGE_CATALOG
from app.models.journal_entry import JournalEntry
from app.models.sentiment import Sentiment
from app.models.user_challenge import UserChallenge
from app.models.weekly_summary import WeeklySummary
from app.services import xp_service


def _week_bounds(day: date) -> tuple[date, date]:
    start = day - timedelta(days=day.weekday())
    return start, start + timedelta(days=6)


def _day_start(day: date) -> datetime:
    return datetime.combine(day, time.min)


def _day_end(day: date) -> datetime:
    return datetime.combine(day, time.max)


def ensure_weekly_challenges(
    db: Session, user_id: int, *, today: date | None = None
) -> list[UserChallenge]:
    today = today or date.today()
    start, end = _week_bounds(today)
    rows: list[UserChallenge] = []
    for defn in CHALLENGE_CATALOG:
        if defn.period != "week":
            continue
        existing = db.scalar(
            select(UserChallenge).where(
                UserChallenge.user_id == user_id,
                UserChallenge.challenge_key == defn.key,
                UserChallenge.starts_on == start,
            )
        )
        if existing is None:
            existing = UserChallenge(
                user_id=user_id,
                challenge_key=defn.key,
                starts_on=start,
                ends_on=end,
                progress=0,
                target=defn.target,
                completed=False,
            )
            db.add(existing)
            db.commit()
            db.refresh(existing)
        rows.append(existing)
    return rows


def _metric_progress(db: Session, user_id: int, metric: str, start: date, end: date) -> int:
    if metric == "journal_days":
        rows = db.scalars(
            select(JournalEntry.created_at).where(
                JournalEntry.user_id == user_id,
                JournalEntry.created_at >= _day_start(start),
                JournalEntry.created_at <= _day_end(end),
            )
        ).all()
        return len({dt.date() for dt in rows})

    if metric == "analyze_count":
        result = db.execute(
            select(JournalEntry.id, JournalEntry.created_at).where(JournalEntry.user_id == user_id)
        ).all()
        ids = [jid for jid, created in result if start <= created.date() <= end]
        if not ids:
            return 0
        return (
            db.scalar(select(func.count()).select_from(Sentiment).where(Sentiment.journal_id.in_(ids)))
            or 0
        )

    if metric == "weekly_summary":
        return (
            db.scalar(
                select(func.count())
                .select_from(WeeklySummary)
                .where(
                    WeeklySummary.user_id == user_id,
                    WeeklySummary.week_start == start,
                )
            )
            or 0
        )

    return 0


def refresh_challenge_progress(db: Session, user_id: int) -> list[UserChallenge]:
    rows = ensure_weekly_challenges(db, user_id)
    for row in rows:
        defn = CHALLENGE_BY_KEY.get(row.challenge_key)
        if not defn:
            continue
        was_completed = row.completed
        progress = _metric_progress(db, user_id, defn.metric, row.starts_on, row.ends_on)
        row.progress = min(progress, row.target)
        just_completed = False
        if not row.completed and row.progress >= row.target:
            row.completed = True
            just_completed = True
        db.add(row)
        db.commit()
        db.refresh(row)
        if just_completed and not was_completed:
            xp_service.award_xp(db, user_id, "challenge_completed", defn.xp_reward)
    return rows


def list_challenges(db: Session, user_id: int) -> dict:
    rows = refresh_challenge_progress(db, user_id)
    challenges = []
    for row in rows:
        defn = CHALLENGE_BY_KEY[row.challenge_key]
        challenges.append(
            {
                "key": row.challenge_key,
                "title": defn.title,
                "description": defn.description,
                "period": defn.period,
                "target": row.target,
                "progress": row.progress,
                "completed": row.completed,
                "xp_reward": defn.xp_reward,
                "starts_on": row.starts_on,
                "ends_on": row.ends_on,
            }
        )
    return {"challenges": challenges}
