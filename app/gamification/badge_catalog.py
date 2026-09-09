"""Static badge catalog — image_key maps to frontend PNG filenames (no extension)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BadgeDef:
    key: str
    title: str
    description: str
    rarity: str  # bronze | silver | gold | platinum
    image_key: str


BADGE_CATALOG: list[BadgeDef] = [
    BadgeDef(
        "first_journal",
        "First Journal",
        "Write your first journal entry.",
        "bronze",
        "bronze-journal-v2",
    ),
    BadgeDef(
        "first_star",
        "First Star",
        "Analyze your first entry.",
        "bronze",
        "bronze-star",
    ),
    BadgeDef(
        "starter_streak",
        "Starter Streak",
        "Reach a 3-day journaling streak.",
        "bronze",
        "bronze-streak",
    ),
    BadgeDef(
        "week_weaver",
        "Week Weaver",
        "Generate your first weekly summary.",
        "silver",
        "silver-calendar",
    ),
    BadgeDef(
        "pattern_search",
        "Pattern Search",
        "Generate your first insight.",
        "silver",
        "silver-search",
    ),
    BadgeDef(
        "steady_writer",
        "Steady Writer",
        "Write 10 journal entries.",
        "gold",
        "gold-journal",
    ),
    BadgeDef(
        "rising_star",
        "Rising Star",
        "Reach a 14-day streak.",
        "gold",
        "gold-starburst",
    ),
    BadgeDef(
        "flame_keeper",
        "Flame Keeper",
        "Reach a 30-day streak.",
        "gold",
        "gold-flame",
    ),
    BadgeDef(
        "deep_insight",
        "Deep Insight",
        "Generate insights 3 times.",
        "platinum",
        "platinum-insight",
    ),
    BadgeDef(
        "star_crown",
        "Star Crown",
        "Reach a 100-day streak.",
        "platinum",
        "platinum-stars-crown",
    ),
    BadgeDef(
        "laurel_legend",
        "Laurel Legend",
        "Reach level Steady Guide (or 700 XP).",
        "platinum",
        "platinum-laurel",
    ),
]

BADGE_BY_KEY = {b.key: b for b in BADGE_CATALOG}
