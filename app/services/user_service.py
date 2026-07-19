"""User business logic / CRUD."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


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
    )
    db.add(user)
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
    if data.get("password"):
        user.password_hash = hash_password(data["password"])

    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user: User) -> None:
    db.delete(user)
    db.commit()
