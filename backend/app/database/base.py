"""
Declarative base for all SQLAlchemy ORM models.

All models must inherit from Base.  Alembic uses Base.metadata to discover
tables during migration generation, so every model module must be imported
before `Base.metadata` is inspected.  Use `import_all_models()` for that.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy ORM models.
    Provides shared configuration and metadata.
    """
    pass


def import_all_models() -> None:
    """
    Import every model module so their tables are registered on Base.metadata.
    Call this before Alembic autogenerate or create_all().
    """
    import app.models  # noqa: F401 — side-effect: registers all models
