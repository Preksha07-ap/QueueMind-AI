"""
Database engine, session factory, and FastAPI dependency.

Connection errors are caught early so the application starts with a clear
message rather than a cryptic traceback deep inside a request handler.
"""

import logging
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Engine ─────────────────────────────────────────────────────────────────────
engine = create_engine(
    settings.database_url,
    # Verify the connection is still alive before handing it out from the pool
    pool_pre_ping=True,
    # Recycle connections after 1 hour to avoid "MySQL server has gone away"
    pool_recycle=3600,
    # Keep a small pool appropriate for a development/single-node setup
    pool_size=5,
    max_overflow=10,
    # Log SQL only in debug mode
    echo=settings.DEBUG,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# ── FastAPI dependency ─────────────────────────────────────────────────────────
def get_db() -> Generator[Session, None, None]:
    """
    Yield a database session per request and guarantee it is closed afterward.
    Usage:
        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError as exc:
        logger.error("Database session error: %s", exc)
        db.rollback()
        raise
    finally:
        db.close()


# ── Health helper ──────────────────────────────────────────────────────────────
def check_db_connection() -> dict:
    """
    Execute a trivial query to verify the database is reachable.
    Returns a dict with keys: connected (bool), detail (str).
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 AS ping"))
            row = result.fetchone()
            if row and row[0] == 1:
                return {"connected": True, "detail": "MySQL connection successful"}
            return {"connected": False, "detail": "Unexpected response from database"}
    except OperationalError as exc:
        logger.error("Database connection failed: %s", exc)
        return {"connected": False, "detail": str(exc.orig) if exc.orig else str(exc)}
    except SQLAlchemyError as exc:
        logger.error("SQLAlchemy error during health check: %s", exc)
        return {"connected": False, "detail": str(exc)}
