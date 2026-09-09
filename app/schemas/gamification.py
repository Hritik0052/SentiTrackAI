"""Gamification API schemas (streaks, XP, badges, challenges)."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


# --- Streaks 2.0 ---

STREAK_MILESTONES = (3, 7, 14, 30, 100)


class StreakStatus(BaseModel):
    current_streak: int
    longest_streak: int
    freeze_tokens: int
    freezes_used_total: int
    last_entry_date: date | None
    is_paused: bool = Field(
        description="True when yesterday was missed but a freeze covered the gap",
    )
    milestones_reached: list[int]
    next_milestone: int | None
    days_to_next_milestone: int | None
    near_milestone_hint: str | None


# --- XP / Levels ---

class XpStatus(BaseModel):
    total_xp: int
    level: int
    level_name: str
    xp_into_level: int
    xp_for_next_level: int | None
    progress_percent: float


class XpEventOut(BaseModel):
    id: int
    action: str
    amount: int
    created_at: datetime

    model_config = {"from_attributes": True}


class XpStatusWithRecent(XpStatus):
    recent_events: list[XpEventOut] = Field(default_factory=list)


# --- Badges ---

class BadgeDefinitionOut(BaseModel):
    key: str
    title: str
    description: str
    rarity: str
    image_key: str


class UserBadgeOut(BaseModel):
    key: str
    title: str
    description: str
    rarity: str
    image_key: str
    unlocked: bool
    unlocked_at: datetime | None = None


class BadgeListOut(BaseModel):
    badges: list[UserBadgeOut]
    unlocked_count: int
    total_count: int


# --- Challenges ---

class ChallengeOut(BaseModel):
    key: str
    title: str
    description: str
    period: str
    target: int
    progress: int
    completed: bool
    xp_reward: int
    starts_on: date
    ends_on: date


class ChallengeListOut(BaseModel):
    challenges: list[ChallengeOut]
