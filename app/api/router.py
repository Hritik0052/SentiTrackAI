"""Aggregate router. Feature routers get wired in here as phases land."""

from fastapi import APIRouter

from app.api.routes import health, users
from app.core.config import settings

# Top-level router (health lives at root, e.g. GET /health).
api_router = APIRouter()
api_router.include_router(health.router)

# Versioned API router (feature modules mount under /api/v1).
v1_router = APIRouter(prefix=settings.api_v1_prefix)
v1_router.include_router(users.router)
# More feature routers (auth, journals, sentiment, ...) are appended in later phases.

api_router.include_router(v1_router)
