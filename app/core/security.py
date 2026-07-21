"""Password hashing (bcrypt) and JWT helpers (PyJWT)."""

from __future__ import annotations

import datetime as dt
import hashlib
import uuid

import bcrypt
import jwt

from app.core.config import settings


# --- Passwords ---------------------------------------------------------------

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# --- JSON Web Tokens ---------------------------------------------------------

def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _encode(subject: str | int, expires_delta: dt.timedelta, token_type: str) -> str:
    expire = _now() + expires_delta
    payload = {
        "sub": str(subject),
        "type": token_type,
        "jti": uuid.uuid4().hex,
        "iat": _now(),
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str | int) -> str:
    return _encode(
        subject,
        dt.timedelta(minutes=settings.access_token_expire_minutes),
        "access",
    )


def create_refresh_token(subject: str | int) -> tuple[str, dt.datetime]:
    """Return (token, expires_at). The token is persisted server-side in Phase 4."""
    expires_at = _now() + dt.timedelta(days=settings.refresh_token_expire_days)
    token = _encode(subject, dt.timedelta(days=settings.refresh_token_expire_days), "refresh")
    return token, expires_at


def decode_token(token: str) -> dict:
    """Decode & validate a JWT. Raises jwt.PyJWTError on failure."""
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


def hash_token(token: str) -> str:
    """SHA-256 digest used to look up/store refresh tokens without keeping raw values."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
