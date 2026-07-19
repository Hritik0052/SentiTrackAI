"""Import all models here so Alembic autogenerate can see them via Base.metadata."""

from app.database.base import Base

# Models are imported as phases land, e.g.:
#   from app.models.user import User
#   from app.models.journal import JournalEntry

__all__ = ["Base"]
