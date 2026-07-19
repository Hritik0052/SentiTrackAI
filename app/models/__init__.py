"""Import all models here so Alembic autogenerate can see them via Base.metadata."""

from app.database.base import Base
from app.models.user import User

__all__ = ["Base", "User"]
