import traceback
import logging
from datetime import datetime
from pathlib import Path
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.database import engine, Base, auto_migrate
from app.api import api_router
from contextlib import asynccontextmanager

# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Create logs dir
_LOG_DIR = Path(__file__).resolve().parents[1] / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)


def _write_startup_log(message: str) -> None:
    try:
        startup_log = _LOG_DIR / "startup_errors.log"
        with startup_log.open("a", encoding="utf-8") as fh:
            fh.write(f"\n--- {datetime.utcnow().isoformat()}Z ---\n{message}\n")
    except Exception:
        pass


# Run auto-migration on module load
try:
    auto_migrate()
    os.makedirs(settings.PDF_STORAGE_DIR, exist_ok=True)
except Exception:
    _write_startup_log(traceback.format_exc())
    raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting up...")
    yield
    logger.info("Application shutting down...")


app = FastAPI(title="Spec Kit Extension - AgentDocx API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def read_root():
    return {"status": "AgentDocx API is running", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


@app.exception_handler(Exception)
async def catch_all_exceptions(request: Request, exc: Exception):
    tb = traceback.format_exc()
    logger.error("=" * 70)
    logger.error(f"UNHANDLED EXCEPTION on {request.method} {request.url}")
    logger.error(f"Exception: {type(exc).__name__}: {exc}")
    logger.error(tb)
    logger.error("=" * 70)
    return JSONResponse(
        status_code=500,
        content={
            "error": type(exc).__name__,
            "message": str(exc),
            "traceback": tb.split("\n")[-10:],
        },
    )