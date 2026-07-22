"""Sentiment ORM model: one AI analysis result per journal entry."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.journal_entry import JournalEntry


class Sentiment(Base, TimestampMixin):
    __tablename__ = "sentiments"

    id: Mapped[int] = mapped_column(primary_key=True)
    # One sentiment per journal entry: unique FK enforces the 1:1 relationship.
    journal_id: Mapped[int] = mapped_column(
        ForeignKey("journal_entries.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    # One of: "positive" | "neutral" | "negative" (validated in AIService).
    sentiment: Mapped[str] = mapped_column(String(20), nullable=False)
    mood: Mapped[str] = mapped_column(String(50), nullable=False)
    emotion: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    # Full raw LLM output, kept for auditing/debugging; not exposed by default.
    raw_response: Mapped[str] = mapped_column(Text, nullable=False)

    journal: Mapped["JournalEntry"] = relationship(back_populates="sentiment")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Sentiment id={self.id} journal_id={self.journal_id} sentiment={self.sentiment!r}>"
