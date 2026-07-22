"""Insight response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class InsightRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    content: str
    created_at: datetime


class InsightListResponse(BaseModel):
    items: list[InsightRead]
    total: int
    page: int
    page_size: int
    total_pages: int
