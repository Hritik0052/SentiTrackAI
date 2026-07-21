"""Auth endpoints: login, refresh, logout."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.auth import LoginRequest, LogoutRequest, RefreshRequest, TokenResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse, summary="Login and obtain a token pair")
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    return auth_service.login(db, str(payload.email), payload.password)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Rotate a refresh token for a new access/refresh pair",
)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    return auth_service.refresh(db, payload.refresh_token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke a refresh token",
)
def logout(payload: LogoutRequest, db: Session = Depends(get_db)) -> None:
    auth_service.logout(db, payload.refresh_token)
