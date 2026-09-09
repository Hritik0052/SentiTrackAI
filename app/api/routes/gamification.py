"""Gamification endpoints: streaks, XP, badges, challenges."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.gamification import (
    BadgeListOut,
    ChallengeListOut,
    StreakStatus,
    XpStatusWithRecent,
)
from app.services import badge_service, challenge_service, streak_service, xp_service

router = APIRouter(prefix="/gamification", tags=["gamification"])


@router.get("/streaks", response_model=StreakStatus, summary="Streaks 2.0 status")
def get_streaks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreakStatus:
    return streak_service.get_streak_status(db, current_user.id)


@router.get("/xp", response_model=XpStatusWithRecent, summary="XP and level progress")
def get_xp(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> XpStatusWithRecent:
    return xp_service.get_xp_status(db, current_user.id)


@router.get("/badges", response_model=BadgeListOut, summary="Badge catalog with unlock state")
def get_badges(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BadgeListOut:
    return badge_service.list_badges(db, current_user.id)


@router.get("/challenges", response_model=ChallengeListOut, summary="Active weekly challenges")
def get_challenges(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChallengeListOut:
    return challenge_service.list_challenges(db, current_user.id)
