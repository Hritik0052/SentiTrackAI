"""Auth business logic: login, refresh-token rotation, logout."""

from __future__ import annotations

import datetime as dt

import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import TokenResponse
from app.services.user_service import get_user_by_email


def _issue_token_pair(db: Session, user: User) -> TokenResponse:
    access_token = create_access_token(user.id)
    refresh_token, expires_at = create_refresh_token(user.id)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            expires_at=expires_at,
        )
    )
    db.commit()
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


def authenticate(db: Session, email: str, password: str) -> User:
    user = get_user_by_email(db, email)
    if user is None or not verify_password(password, user.password_hash):
        raise UnauthorizedError("Invalid email or password")
    return user


def login(db: Session, email: str, password: str) -> TokenResponse:
    user = authenticate(db, email, password)
    return _issue_token_pair(db, user)


def _get_active_refresh_token(db: Session, token: str) -> RefreshToken:
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        raise UnauthorizedError("Invalid or expired refresh token")

    if payload.get("type") != "refresh":
        raise UnauthorizedError("Invalid token type")

    row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(token)))
    if row is None or row.revoked:
        raise UnauthorizedError("Refresh token has been revoked or does not exist")

    expires_at = row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=dt.timezone.utc)
    if expires_at < dt.datetime.now(dt.timezone.utc):
        raise UnauthorizedError("Refresh token expired")

    return row


def refresh(db: Session, token: str) -> TokenResponse:
    """Validate a refresh token, revoke it, and issue a fresh rotated pair."""
    row = _get_active_refresh_token(db, token)
    user = db.get(User, row.user_id)
    if user is None:
        raise UnauthorizedError("User no longer exists")

    row.revoked = True
    db.add(row)
    return _issue_token_pair(db, user)


def logout(db: Session, token: str) -> None:
    """Revoke a refresh token. Idempotent: unknown/already-revoked tokens are a no-op."""
    row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(token)))
    if row is not None and not row.revoked:
        row.revoked = True
        db.commit()
