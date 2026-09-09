"""Weekly challenge definitions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChallengeDef:
    key: str
    title: str
    description: str
    period: str  # week | month
    target: int
    xp_reward: int
    metric: str  # journal_days | analyze_count | weekly_summary


CHALLENGE_CATALOG: list[ChallengeDef] = [
    ChallengeDef(
        "journal_4_days",
        "Journal 4 days",
        "Write on at least 4 different days this week.",
        "week",
        4,
        25,
        "journal_days",
    ),
    ChallengeDef(
        "analyze_all_week",
        "Analyze your week",
        "Analyze at least 3 entries this week.",
        "week",
        3,
        20,
        "analyze_count",
    ),
    ChallengeDef(
        "weekly_wrap",
        "Sunday wrap",
        "Generate a weekly summary this week.",
        "week",
        1,
        15,
        "weekly_summary",
    ),
]

CHALLENGE_BY_KEY = {c.key: c for c in CHALLENGE_CATALOG}
