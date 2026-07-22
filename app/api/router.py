"""Aggregate router. Feature routers get wired in here as phases land."""

from fastapi import APIRouter

from app.api.routes import (
    analytics,
    auth,
    health,
    insights,
    journals,
    search,
    summary,
    users,
)
from app.core.config import settings

# Top-level router (health lives at root, e.g. GET /health).
api_router = APIRouter()
api_router.include_router(health.router)

# Versioned API router (feature modules mount under /api/v1).
v1_router = APIRouter(prefix=settings.api_v1_prefix)
v1_router.include_router(auth.router)
v1_router.include_router(users.router)
v1_router.include_router(journals.router)
v1_router.include_router(summary.router)
v1_router.include_router(analytics.router)
v1_router.include_router(search.router)
v1_router.include_router(insights.router)

api_router.include_router(v1_router)
