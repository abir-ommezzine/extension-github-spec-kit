"""
database.py — Auto-migration + SQLAlchemy engine/session setup.
Every time the app starts, Base.metadata.create_all() runs automatically.
No manual alembic commands needed.
"""

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

DATABASE_URL = settings.DATABASE_URL
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def auto_migrate():
    """Automatically creates all tables on startup. Preserves existing data."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info("[AUTO-MIGRATE] Checking database schema...")

    import app.models  # noqa: F401 — registers all models with Base.metadata
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    existing = inspector.get_table_names()
    expected = ["projects", "artifacts", "doc_versions", "pipeline_runs"]

    for table in expected:
        status = "OK" if table in existing else "MISSING"
        logger.info(f"  [{status}] Table '{table}'")

    logger.info("[AUTO-MIGRATE] Done.")
    return True