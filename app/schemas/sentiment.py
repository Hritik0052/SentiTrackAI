"""Sentiment response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SentimentRead(BaseModel):
    """AI analysis result for a single journal entry.

    ``raw_response`` (the full LLM payload) is intentionally omitted — it is stored
    for auditing but never returned to clients.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    journal_id: int
    sentiment: str = Field(examples=["positive"], description="positive | neutral | negative")
    mood: str = Field(examples=["content"])
    emotion: str = Field(examples=["gratitude"])
    confidence: float = Field(examples=[0.87], ge=0.0, le=1.0)
    created_at: datetime
    updated_at: datetime
