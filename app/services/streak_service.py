"""Streaks 2.0: soft freezes, milestones, cached streak profile."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.journal_entry import JournalEntry
from app.models.streak_profile import StreakProfile
from app.schemas.gamification import STREAK_MILESTONES


def _entry_dates(db: Session, user_id: int) -> list[date]:
    rows = db.scalars(
        select(JournalEntry.created_at)
        .where(JournalEntry.user_id == user_id)
        .order_by(JournalEntry.created_at.asc())
    ).all()
    return sorted({dt.date() for dt in rows})


def _longest_run(dates: list[date]) -> int:
    if not dates:
        return 0
    longest = run = 1
    for prev, cur in zip(dates, dates[1:]):
        run = run + 1 if (cur - prev).days == 1 else 1
        longest = max(longest, run)
    return longest


def _trailing_run_ending_at(dates: list[date], end: date) -> int:
    """Length of consecutive days ending on `end` (must be in set or 0)."""
    date_set = set(dates)
    if end not in date_set:
        return 0
    run = 0
    day = end
    while day in date_set:
        run += 1
        day -= timedelta(days=1)
    return run


def get_or_create_streak_profile(db: Session, user_id: int) -> StreakProfile:
    profile = db.scalar(select(StreakProfile).where(StreakProfile.user_id == user_id))
    if profile is None:
        profile = StreakProfile(user_id=user_id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def refresh_streak_profile(db: Session, user_id: int) -> StreakProfile:
    """Recompute streak using soft freezes (auto-spend 1 token for a 1-day gap)."""
    profile = get_or_create_streak_profile(db, user_id)
    dates = _entry_dates(db, user_id)
    today = date.today()
    longest = _longest_run(dates)

    if not dates:
        profile.current_streak = 0
        profile.longest_streak = 0
        profile.last_entry_date = None
        db.commit()
        db.refresh(profile)
        return profile

    last = dates[-1]
    profile.last_entry_date = last

    # Soft streak: allow today or yesterday; if gap is exactly 1 day beyond yesterday
    # and freezes remain, consume one freeze and treat as continuous from last entry.
    gap = (today - last).days
    is_paused = False

    if gap <= 1:
        # Active: streak ends at last entry day (or today if they wrote today).
        anchor = last
        current = _trailing_run_ending_at(dates, anchor)
    elif gap == 2 and profile.freeze_tokens > 0:
        # Missed exactly one calendar day → spend freeze, keep streak from last entry.
        if profile.last_freeze_on != today:
            profile.freeze_tokens -= 1
            profile.freezes_used_total += 1
            profile.last_freeze_on = today
        is_paused = True
        current = _trailing_run_ending_at(dates, last)
    else:
        current = 0

    # Earn a freeze when streak first reaches 7, 14, 21… (cap tokens at 2).
    earn_at = (current // 7) * 7
    if earn_at >= 7 and earn_at > profile.freeze_earn_watermark and profile.freeze_tokens < 2:
        profile.freeze_tokens = min(2, profile.freeze_tokens + 1)
        profile.freeze_earn_watermark = earn_at

    profile.current_streak = current
    profile.longest_streak = max(longest, current, profile.longest_streak)
    db.commit()
    db.refresh(profile)
    # Attach ephemeral pause flag for response building (not a column).
    profile._is_paused = is_paused  # type: ignore[attr-defined]
    return profile


def get_streak_status(db: Session, user_id: int) -> dict:
    profile = refresh_streak_profile(db, user_id)
    current = profile.current_streak
    reached = [m for m in STREAK_MILESTONES if m <= max(current, profile.longest_streak)]
    # Next milestone based on current streak progress
    next_m = next((m for m in STREAK_MILESTONES if m > current), None)
    days_to = (next_m - current) if next_m is not None else None
    hint = None
    if days_to == 1:
        hint = f"You're 1 day from a {next_m}-day streak"
    elif days_to is not None and days_to <= 3:
        hint = f"{days_to} days to your {next_m}-day milestone"

    return {
        "current_streak": current,
        "longest_streak": profile.longest_streak,
        "freeze_tokens": profile.freeze_tokens,
        "freezes_used_total": profile.freezes_used_total,
        "last_entry_date": profile.last_entry_date,
        "is_paused": bool(getattr(profile, "_is_paused", False)),
        "milestones_reached": reached,
        "next_milestone": next_m,
        "days_to_next_milestone": days_to,
        "near_milestone_hint": hint,
    }


def on_journal_created(db: Session, user_id: int) -> None:
    """Call after a new journal entry is committed."""
    refresh_streak_profile(db, user_id)
