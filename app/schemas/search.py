"""Search request/response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.sentiment import SentimentRead


class SearchResultItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str | None
    content: str
    created_at: datetime
    updated_at: datetime
    # Nested analysis when the entry has been analyzed; null otherwise.
    sentiment: SentimentRead | None = None


class SearchResponse(BaseModel):
    items: list[SearchResultItem]
    total: int
    page: int
    page_size: int
    total_pages: int
