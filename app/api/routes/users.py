"""User endpoints: registration + self-management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.billing import UsageSnapshot
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services import billing_service, user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> UserRead:
    user = user_service.create_user(db, payload)
    return user_service.to_user_read(db, user)


@router.get("/me", response_model=UserRead, summary="Get current user")
def read_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserRead:
    return user_service.to_user_read(db, current_user)


@router.get("/me/usage", response_model=UsageSnapshot, summary="Current plan usage quotas")
def read_my_usage(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UsageSnapshot:
    return billing_service.get_usage_snapshot(db, current_user.id)


@router.put("/me", response_model=UserRead, summary="Update current user")
def update_me(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserRead:
    user = user_service.update_user(db, current_user, payload)
    return user_service.to_user_read(db, user)


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete current user",
)
def delete_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    user_service.delete_user(db, current_user)
