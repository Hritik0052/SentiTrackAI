"""Sentiment business logic: run AI analysis on an owned journal entry and store it.

Analysis is 1:1 with a journal entry. Re-analyzing an already-analyzed entry
overwrites the previous result (upsert) rather than creating a duplicate, so a row
in ``sentiments`` always reflects the latest analysis of its entry's content.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.sentiment import Sentiment
from app.services import ai_service, journal_service


def analyze_journal(db: Session, user_id: int, journal_id: int) -> Sentiment:
    """Analyze an owned journal entry and upsert its sentiment row.

    Raises ``NotFoundError`` if the entry doesn't exist or isn't owned by the user,
    and ``AIServiceError`` (502) if the AI provider fails or returns garbage.
    """
    entry = journal_service.get_journal(db, user_id, journal_id)
    result = ai_service.analyze_sentiment(entry.content)

    sentiment = entry.sentiment
    if sentiment is None:
        sentiment = Sentiment(journal_id=entry.id)
        db.add(sentiment)

    sentiment.sentiment = result["sentiment"]
    sentiment.mood = result["mood"]
    sentiment.emotion = result["emotion"]
    sentiment.confidence = result["confidence"]
    sentiment.raw_response = result["raw_response"]

    db.commit()
    db.refresh(sentiment)
    return sentiment


def get_sentiment(db: Session, user_id: int, journal_id: int) -> Sentiment:
    """Return the stored sentiment for an owned entry, or 404 if not yet analyzed."""
    entry = journal_service.get_journal(db, user_id, journal_id)
    if entry.sentiment is None:
        raise NotFoundError("This journal entry has not been analyzed yet")
    return entry.sentiment
