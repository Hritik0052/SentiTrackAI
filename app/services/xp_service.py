"""XP awards and level calculation."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.xp_event import XpEvent
from app.models.xp_profile import XpProfile

# Cumulative XP thresholds to *enter* each level (level 1 = Seeker at 0).
LEVELS: list[tuple[int, str, int]] = [
    (1, "Seeker", 0),
    (2, "Observer", 50),
    (3, "Reflector", 150),
    (4, "Insightful", 350),
    (5, "Steady Guide", 700),
]

XP_REWARDS: dict[str, int] = {
    "journal_created": 10,
    "sentiment_analyzed": 5,
    "weekly_summary": 15,
    "insights_generated": 20,
    "challenge_completed": 25,
}


def _level_for_xp(total_xp: int) -> tuple[int, str, int, int | None]:
    """Return (level, name, xp_into_level, xp_needed_for_next or None)."""
    current = LEVELS[0]
    for lvl in LEVELS:
        if total_xp >= lvl[2]:
            current = lvl
        else:
            break
    level, name, floor = current
    # Next threshold
    next_floor = None
    for lvl in LEVELS:
        if lvl[2] > floor:
            next_floor = lvl[2]
            break
    into = total_xp - floor
    need = (next_floor - floor) if next_floor is not None else None
    return level, name, into, need


def get_or_create_xp_profile(db: Session, user_id: int) -> XpProfile:
    profile = db.scalar(select(XpProfile).where(XpProfile.user_id == user_id))
    if profile is None:
        profile = XpProfile(user_id=user_id, total_xp=0)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def award_xp(db: Session, user_id: int, action: str, amount: int | None = None) -> XpProfile:
    profile = get_or_create_xp_profile(db, user_id)
    xp = amount if amount is not None else XP_REWARDS.get(action, 0)
    if xp <= 0:
        return profile
    profile.total_xp += xp
    db.add(XpEvent(profile_id=profile.id, user_id=user_id, action=action, amount=xp))
    db.commit()
    db.refresh(profile)
    return profile


def get_xp_status(db: Session, user_id: int, *, include_recent: bool = True) -> dict:
    profile = get_or_create_xp_profile(db, user_id)
    level, name, into, need = _level_for_xp(profile.total_xp)
    percent = 100.0 if need is None else round(min(100.0, (into / need) * 100), 1)
    payload: dict = {
        "total_xp": profile.total_xp,
        "level": level,
        "level_name": name,
        "xp_into_level": into,
        "xp_for_next_level": need,
        "progress_percent": percent,
    }
    if include_recent:
        events = db.scalars(
            select(XpEvent)
            .where(XpEvent.user_id == user_id)
            .order_by(XpEvent.created_at.desc())
            .limit(10)
        ).all()
        payload["recent_events"] = events
    return payload
