"""Journal entry request/response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class JournalBase(BaseModel):
    title: str | None = Field(default=None, max_length=200, examples=["A good day"])
    content: str = Field(min_length=1, max_length=10_000, examples=["Today I felt calm and productive."])


class JournalCreate(JournalBase):
    pass


class JournalUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    content: str | None = Field(default=None, min_length=1, max_length=10_000)


class JournalRead(JournalBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class JournalListResponse(BaseModel):
    items: list[JournalRead]
    total: int
    page: int
    page_size: int
    total_pages: int
