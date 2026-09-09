"""Award and list user badges."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.gamification.badge_catalog import BADGE_BY_KEY, BADGE_CATALOG
from app.models.insight import Insight
from app.models.journal_entry import JournalEntry
from app.models.sentiment import Sentiment
from app.models.streak_profile import StreakProfile
from app.models.user_badge import UserBadge
from app.models.weekly_summary import WeeklySummary
from app.models.xp_profile import XpProfile
from app.services import streak_service


def _unlock(db: Session, user_id: int, badge_key: str) -> bool:
    if badge_key not in BADGE_BY_KEY:
        return False
    exists = db.scalar(
        select(UserBadge.id).where(
            UserBadge.user_id == user_id,
            UserBadge.badge_key == badge_key,
        )
    )
    if exists:
        return False
    db.add(UserBadge(user_id=user_id, badge_key=badge_key))
    db.commit()
    return True


def evaluate_badges(db: Session, user_id: int) -> list[str]:
    """Check catalog rules; return newly unlocked keys."""
    newly: list[str] = []

    journal_count = db.scalar(
        select(func.count()).select_from(JournalEntry).where(JournalEntry.user_id == user_id)
    ) or 0
    analyzed_count = db.scalar(
        select(func.count())
        .select_from(Sentiment)
        .join(JournalEntry, JournalEntry.id == Sentiment.journal_id)
        .where(JournalEntry.user_id == user_id)
    ) or 0
    summary_count = db.scalar(
        select(func.count()).select_from(WeeklySummary).where(WeeklySummary.user_id == user_id)
    ) or 0
    insight_count = db.scalar(
        select(func.count()).select_from(Insight).where(Insight.user_id == user_id)
    ) or 0

    streak = streak_service.get_or_create_streak_profile(db, user_id)
    # Prefer refreshed values
    streak_service.refresh_streak_profile(db, user_id)
    db.refresh(streak)
    best_streak = max(streak.current_streak, streak.longest_streak)

    xp_profile = db.scalar(select(XpProfile).where(XpProfile.user_id == user_id))
    total_xp = xp_profile.total_xp if xp_profile else 0

    checks: list[tuple[str, bool]] = [
        ("first_journal", journal_count >= 1),
        ("first_star", analyzed_count >= 1),
        ("starter_streak", best_streak >= 3),
        ("week_weaver", summary_count >= 1),
        ("pattern_search", insight_count >= 1),
        ("steady_writer", journal_count >= 10),
        ("rising_star", best_streak >= 14),
        ("flame_keeper", best_streak >= 30),
        ("deep_insight", insight_count >= 3),
        ("star_crown", best_streak >= 100),
        ("laurel_legend", total_xp >= 700),
    ]

    for key, ok in checks:
        if ok and _unlock(db, user_id, key):
            newly.append(key)
    return newly


def list_badges(db: Session, user_id: int) -> dict:
    evaluate_badges(db, user_id)
    unlocked_rows = db.scalars(select(UserBadge).where(UserBadge.user_id == user_id)).all()
    unlocked_map = {row.badge_key: row for row in unlocked_rows}

    badges = []
    for defn in BADGE_CATALOG:
        row = unlocked_map.get(defn.key)
        badges.append(
            {
                "key": defn.key,
                "title": defn.title,
                "description": defn.description,
                "rarity": defn.rarity,
                "image_key": defn.image_key,
                "unlocked": row is not None,
                "unlocked_at": row.created_at if row else None,
            }
        )
    return {
        "badges": badges,
        "unlocked_count": sum(1 for b in badges if b["unlocked"]),
        "total_count": len(badges),
    }
