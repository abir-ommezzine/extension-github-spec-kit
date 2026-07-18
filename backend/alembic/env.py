from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys
import logging

# Ensure project path is on sys.path so `app` package imports work
here = os.path.dirname(__file__)
backend_dir = os.path.dirname(here)  # <repo>/backend
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

try:
    # Import application metadata and settings
    from app.database import Base
    from app.config import settings
    # Import models to ensure they are registered on Base.metadata
    from app import models as _models  # noqa: F401
except Exception as exc:  # pragma: no cover - helpful runtime error
    logging.error("Failed to import app models/settings for Alembic autogenerate: %s", exc)
    raise

# Alembic Config object
config = context.config

# Normalize DATABASE_URL to a SQLAlchemy driver URL (match backend/app/database.py logic)
sqlalchemy_url = settings.DATABASE_URL
if sqlalchemy_url.startswith("postgresql://"):
    sqlalchemy_url = sqlalchemy_url.replace("postgresql://", "postgresql+psycopg2://", 1)
elif sqlalchemy_url.startswith("postgres://"):
    sqlalchemy_url = sqlalchemy_url.replace("postgres://", "postgresql+psycopg2://", 1)

# Override the DB URL from application settings
config.set_main_option("sqlalchemy.url", sqlalchemy_url)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
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