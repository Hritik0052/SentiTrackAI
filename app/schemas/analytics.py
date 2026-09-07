"""Analytics response schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class LabelCount(BaseModel):
    label: str
    count: int


class DashboardAnalytics(BaseModel):
    total_entries: int
    analyzed_entries: int
    sentiment_counts: dict[str, int] = Field(
        description="Counts keyed by positive | neutral | negative",
        examples=[{"positive": 5, "neutral": 2, "negative": 1}],
    )
    average_confidence: float | None
    most_common_emotion: str | None
    most_common_mood: str | None
    current_streak: int = Field(description="Consecutive days with an entry, ending today/yesterday")
    longest_streak: int = Field(description="Longest run of consecutive days with an entry")
    entries_this_week: int
    entries_this_month: int
    first_entry_at: datetime | None
    last_entry_at: datetime | None


class MoodDistribution(BaseModel):
    total_analyzed: int
    sentiment_counts: dict[str, int]
    emotions: list[LabelCount]
    moods: list[LabelCount]


class PeriodStat(BaseModel):
    period: str = Field(description="`YYYY-MM` for monthly, `YYYY` for yearly", examples=["2026-07"])
    entries: int
    analyzed: int
    sentiment_counts: dict[str, int]
    average_confidence: float | None
    most_common_emotion: str | None


class MonthlyAnalytics(BaseModel):
    year: int
    months: list[PeriodStat]


class YearlyAnalytics(BaseModel):
    years: list[PeriodStat]


class MoodTrendSeries(BaseModel):
    sentiment: list[str] = Field(description="Always positive, neutral, negative")
    emotions: list[str] = Field(description="Top emotion labels in the selected range")


class MoodTrendTotals(BaseModel):
    entries: int
    analyzed: int
    sentiment_counts: dict[str, int]
    emotion_counts: dict[str, int]


class MoodTrendBucket(BaseModel):
    date: date
    sentiment: dict[str, int]
    emotions: dict[str, int]


class MoodTrends(BaseModel):
    period: Literal["week", "month", "custom"]
    start: date
    end: date
    granularity: Literal["day"] = "day"
    buckets: list[MoodTrendBucket]
    series: MoodTrendSeries
    totals: MoodTrendTotals
