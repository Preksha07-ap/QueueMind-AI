"""
Alembic environment configuration for QueueMind AI.

Key responsibilities
--------------------
1. Load database URL from application settings (reads .env automatically).
2. Import every SQLAlchemy model so Alembic can detect schema changes.
3. Configure both offline (SQL dump) and online (live connection) migration modes.
"""

import sys
import os

# Allow `app.*` imports when running alembic from the backend/ directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# ── Load application settings ─────────────────────────────────────────────────
from app.core.config import settings

# ── Import all models so their tables appear in Base.metadata ─────────────────
from app.database.base import Base, import_all_models
import_all_models()

# ── Alembic Config object ─────────────────────────────────────────────────────
config = context.config

# Override the sqlalchemy.url in alembic.ini with our environment-driven URL
config.set_main_option("sqlalchemy.url", settings.database_url)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate support
target_metadata = Base.metadata


# ── Offline migrations ────────────────────────────────────────────────────────
def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    Generates SQL without connecting to the database.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online migrations ─────────────────────────────────────────────────────────
def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.
    Establishes a real connection and applies changes.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
