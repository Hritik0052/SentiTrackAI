"""Authentication dependency: resolve the current user from a Bearer token."""

from __future__ import annotations

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import UnauthorizedError
from app.core.security import decode_token
from app.database import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.api_v1_prefix}/auth/login",
    auto_error=False,
)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not token:
        raise UnauthorizedError("Not authenticated")

    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        raise UnauthorizedError("Invalid or expired token")

    if payload.get("type") != "access":
        raise UnauthorizedError("Invalid token type")

    subject = payload.get("sub")
    if subject is None:
        raise UnauthorizedError("Invalid token payload")

    user = db.get(User, int(subject))
    if user is None:
        raise UnauthorizedError("User no longer exists")
    return user
