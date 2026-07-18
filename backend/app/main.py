
import traceback
from datetime import datetime
from pathlib import Path
import os

try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from app.config import settings
    from app.database import engine, Base
    from app.api import api_router
    from contextlib import asynccontextmanager
    from alembic.config import Config
    from alembic import command

    # Create logs dir for startup errors
    _LOG_DIR = Path(__file__).resolve().parents[1] / "logs"
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    _STARTUP_LOG = _LOG_DIR / "startup_errors.log"

    # rest of module follows in try block
except Exception:
    # If imports fail at module import time, log the traceback to a file for debugging
    try:
        log_dir = Path(__file__).resolve().parents[1] / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        startup_log = log_dir / "startup_errors.log"
        with startup_log.open("a", encoding="utf-8") as fh:
            fh.write("\n--- STARTUP IMPORT ERROR ---\n")
            fh.write(f"timestamp: {datetime.utcnow().isoformat()}Z\n")
            fh.write(traceback.format_exc())
            fh.write("\n")
    except Exception:
        pass
    raise

def _write_startup_log(message: str) -> None:
    try:
        log_dir = Path(__file__).resolve().parents[1] / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        startup_log = log_dir / "startup_errors.log"
        with startup_log.open("a", encoding="utf-8") as fh:
            fh.write("\n--- STARTUP ERROR ---\n")
            fh.write(f"timestamp: {datetime.utcnow().isoformat()}Z\n")
            fh.write(message)
            fh.write("\n")
    except Exception:
        pass


try:
    # Create tables on startup (sync version)
    Base.metadata.create_all(bind=engine)

    # Create PDF storage directory
    os.makedirs(settings.PDF_STORAGE_DIR, exist_ok=True)
except Exception:
    _write_startup_log(traceback.format_exc())
    raise

def run_migrations():
    """Run Alembic migrations automatically on startup."""
    try:
        ini_path = os.path.join(os.path.dirname(__file__), "..", "alembic.ini")
        alembic_cfg = Config(ini_path)
        # Ensure the script_location is correct relative to the ini file
        alembic_cfg.set_main_option(
            "script_location", os.path.join(os.path.dirname(__file__), "..", "alembic")
        )
        command.upgrade(alembic_cfg, "head")
    except Exception:
        _write_startup_log(traceback.format_exc())
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    run_migrations()
    yield
    # Shutdown (nothing needed)


# Create application with lifespan handler
app = FastAPI(title="Spec Kit Extension - AgentDocx API", lifespan=lifespan)

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def read_root():
    return {"status": "AgentDocx API is running", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}