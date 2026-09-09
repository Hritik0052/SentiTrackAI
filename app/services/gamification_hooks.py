"""Side-effects after core actions: streaks, XP, badges, challenges."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.services import badge_service, challenge_service, streak_service, xp_service


def after_journal_created(db: Session, user_id: int) -> None:
    streak_service.on_journal_created(db, user_id)
    xp_service.award_xp(db, user_id, "journal_created")
    badge_service.evaluate_badges(db, user_id)
    challenge_service.refresh_challenge_progress(db, user_id)


def after_sentiment_analyzed(db: Session, user_id: int) -> None:
    xp_service.award_xp(db, user_id, "sentiment_analyzed")
    badge_service.evaluate_badges(db, user_id)
    challenge_service.refresh_challenge_progress(db, user_id)


def after_weekly_summary(db: Session, user_id: int) -> None:
    xp_service.award_xp(db, user_id, "weekly_summary")
    badge_service.evaluate_badges(db, user_id)
    challenge_service.refresh_challenge_progress(db, user_id)


def after_insights_generated(db: Session, user_id: int) -> None:
    xp_service.award_xp(db, user_id, "insights_generated")
    badge_service.evaluate_badges(db, user_id)
