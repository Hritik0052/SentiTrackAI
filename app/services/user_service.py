"""User business logic / CRUD."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import ChangePasswordRequest, UserCreate, UserRead, UserUpdate
from app.services import billing_service


def get_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found")
    return user


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def create_user(db: Session, payload: UserCreate) -> User:
    if get_user_by_email(db, str(payload.email)):
        raise ConflictError("Email already registered")
    user = User(
        name=payload.name,
        email=str(payload.email),
        password_hash=hash_password(payload.password),
        is_admin=False,
    )
    db.add(user)
    db.flush()
    billing_service.assign_default_plan(db, user, commit=False)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user: User, payload: UserUpdate) -> User:
    data = payload.model_dump(exclude_unset=True)

    new_email = data.get("email")
    if new_email and new_email != user.email:
        if get_user_by_email(db, str(new_email)):
            raise ConflictError("Email already registered")
        user.email = str(new_email)

    if data.get("name"):
        user.name = data["name"]

    db.commit()
    db.refresh(user)
    return user


def change_password(db: Session, user: User, payload: ChangePasswordRequest) -> None:
    if not verify_password(payload.current_password, user.password_hash):
        raise BadRequestError("Current password is incorrect")
    if payload.current_password == payload.new_password:
        raise BadRequestError("New password must be different from the current password")
    user.password_hash = hash_password(payload.new_password)
    db.commit()


def delete_user(db: Session, user: User) -> None:
    db.delete(user)
    db.commit()


def to_user_read(db: Session, user: User) -> UserRead:
    plan = billing_service.get_user_plan(db, user.id)
    return UserRead(
        id=user.id,
        name=user.name,
        email=user.email,
        is_admin=bool(user.is_admin),
        plan=billing_service.to_plan_summary(plan) if plan else None,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )
