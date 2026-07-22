"""Weekly summary request/response schemas."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class WeeklySummaryGenerate(BaseModel):
    week_of: date | None = Field(
        default=None,
        description="Any date within the target week (Mon–Sun). Defaults to the current week.",
        examples=["2026-07-20"],
    )


class WeeklySummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    week_start: date
    week_end: date
    summary: str
    suggestions: list[str]
    entry_count: int
    created_at: datetime
    updated_at: datetime
