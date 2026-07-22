"""Insight business logic.

`generate_insights` assembles a compact context from the user's aggregate stats
(reusing the Phase 9 analytics dashboard) plus their most recent entries, asks the AI
for natural-language observations, and stores each as an ``insights`` row. Every
generation appends a new batch; `list_insights` pages through them newest-first.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError
from app.dependencies.pagination import PaginationParams
from app.models.insight import Insight
from app.models.journal_entry import JournalEntry
from app.services import ai_service, analytics_service

_RECENT_ENTRY_LIMIT = 10
_CONTENT_PREVIEW_CHARS = 200


def _build_context(db: Session, user_id: int, dashboard: dict) -> str:
    recent = list(
        db.scalars(
            select(JournalEntry)
            .where(JournalEntry.user_id == user_id)
            .order_by(JournalEntry.created_at.desc())
            .limit(_RECENT_ENTRY_LIMIT)
        ).all()
    )
    entry_lines = "\n".join(
        f"- {entry.created_at.date()}: {entry.content[:_CONTENT_PREVIEW_CHARS]}"
        for entry in recent
    )
    return (
        "Journaling statistics:\n"
        f"- total entries: {dashboard['total_entries']}\n"
        f"- analyzed entries: {dashboard['analyzed_entries']}\n"
        f"- sentiment counts: {dashboard['sentiment_counts']}\n"
        f"- average confidence: {dashboard['average_confidence']}\n"
        f"- most common emotion: {dashboard['most_common_emotion']}\n"
        f"- most common mood: {dashboard['most_common_mood']}\n"
        f"- current streak (days): {dashboard['current_streak']}\n"
        f"- longest streak (days): {dashboard['longest_streak']}\n"
        f"- entries this week: {dashboard['entries_this_week']}\n"
        f"- entries this month: {dashboard['entries_this_month']}\n\n"
        f"Most recent entries (newest first):\n{entry_lines}"
    )


def generate_insights(db: Session, user_id: int) -> list[Insight]:
    """Generate and store a fresh batch of insights for the user.

    Raises ``BadRequestError`` if the user has no entries yet, and
    ``AIServiceError`` (502) if the AI provider fails.
    """
    dashboard = analytics_service.get_dashboard(db, user_id)
    if dashboard["total_entries"] == 0:
        raise BadRequestError("No journal entries to generate insights from")

    context = _build_context(db, user_id, dashboard)
    statements = ai_service.generate_insights(context)

    insights = [Insight(user_id=user_id, content=statement) for statement in statements]
    db.add_all(insights)
    db.commit()
    for insight in insights:
        db.refresh(insight)
    return insights


def list_insights(
    db: Session, user_id: int, pagination: PaginationParams
) -> tuple[list[Insight], int]:
    """Return the user's insights, newest first, paginated."""
    stmt = (
        select(Insight)
        .where(Insight.user_id == user_id)
        .order_by(Insight.created_at.desc(), Insight.id.desc())
        .offset(pagination.offset)
        .limit(pagination.limit)
    )
    count_stmt = select(func.count()).select_from(Insight).where(Insight.user_id == user_id)

    items = list(db.scalars(stmt).all())
    total = db.scalar(count_stmt) or 0
    return items, total
