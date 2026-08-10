import os
import json
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base, SessionLocal

import app.models  

# Import du router pipeline (BDD & LangGraph)
from app.api.v1.endpoints import pipeline
from app.api.v1.endpoints import tickets

# 1. Création automatique des tables BDD si elles n'existent pas et synchronisation des ENUMs natifs
Base.metadata.create_all(bind=engine)
app.models.sync_native_enums(engine)

# ── Logging setup ────────────────────────────────────────────────────────────
# Force INFO level so every log line is visible in the uvicorn console.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _get_current_task_file_path() -> Path:
    """Get the current task file path dynamically based on configuration."""
    from app.config import settings
    from app.utils.path_builder import BASE_DIR
    
    # Use TARGET_PROJECT_PATH from config if specified, otherwise fall back to BASE_DIR
    if settings.TARGET_PROJECT_PATH:
        target_dir = Path(settings.TARGET_PROJECT_PATH)
    else:
        target_dir = BASE_DIR
    
    return target_dir / ".task_runtime" / "current-task.json"


def _sync_current_task_to_db() -> dict:
    """
    Read current-task.json and update the matching ticket status.
    Returns a debug dict describing every step taken.
    """
    current_task_file = _get_current_task_file_path()
    
    result = {
        "file_path": str(current_task_file),
        "file_exists": current_task_file.exists(),
        "raw_content": None,
        "parsed": None,
        "task_id": None,
        "project_name": None,
        "target_status": None,
        "project_found": False,
        "project_id": None,
        "all_ticket_source_paths": [],
        "ticket_found": False,
        "ticket_id": None,
        "ticket_current_status": None,
        "action": None,
        "error": None,
    }

    logger.info("=" * 60)
    logger.info("[sync] _sync_current_task_to_db() called")
    logger.info(f"[sync] Checking file: {current_task_file}")
    logger.info(f"[sync] File exists: {result['file_exists']}")

    if not current_task_file.exists():
        result["error"] = "File does not exist"
        logger.error(f"[sync] ABORT — file not found: {current_task_file}")
        return result

    try:
        raw = current_task_file.read_text(encoding="utf-8")
        result["raw_content"] = raw
        logger.info(f"[sync] Raw file content:\n{raw}")
        data = json.loads(raw)
        result["parsed"] = data
        logger.info(f"[sync] Parsed JSON: {data}")
    except (json.JSONDecodeError, OSError) as e:
        result["error"] = str(e)
        logger.error(f"[sync] ABORT — could not read/parse file: {e}")
        return result

    task_id: str = data.get("task_id", "")
    raw_status: str = data.get("status", "in_progress")
    project_name: str = data.get("project_name", "")

    result["task_id"] = task_id
    result["project_name"] = project_name
    result["target_status"] = raw_status

    logger.info(f"[sync] task_id={task_id!r}  status={raw_status!r}  project={project_name!r}")

    if not task_id:
        result["error"] = "task_id is empty"
        logger.error("[sync] ABORT — task_id is empty in current-task.json")
        return result

    from app.models import Ticket, Project, TicketStatus, AuthorType
    from app.services.ticket_ingestion import update_ticket_status

    db = SessionLocal()
    try:
        # ── Project lookup ──────────────────────────────────────────────────
        if project_name:
            project = db.query(Project).filter(Project.name == project_name).first()
            if project:
                result["project_found"] = True
                result["project_id"] = str(project.id)
                logger.info(f"[sync] Project found: {project.name!r} id={project.id}")
            else:
                logger.warning(f"[sync] Project NOT found in DB for name={project_name!r}")
                # Log every project name in DB to spot mismatches
                all_projects = db.query(Project).all()
                names = [p.name for p in all_projects]
                logger.warning(f"[sync] Projects currently in DB: {names}")
        else:
            logger.warning("[sync] project_name is empty — will search across all projects")

        # ── Ticket lookup ───────────────────────────────────────────────────
        # Log ALL ticket source_paths for this project so we can see the exact pattern
        if result["project_id"]:
            sample_tickets = (
                db.query(Ticket)
                .filter(Ticket.project_id == project.id)
                .all()
            )
            result["all_ticket_source_paths"] = [t.source_path for t in sample_tickets]
            logger.info(
                f"[sync] Tickets in project ({len(sample_tickets)} total), source_paths:\n"
                + "\n".join(f"  [{t.status.value}] {t.source_path}" for t in sample_tickets)
            )
        else:
            # No project filter — dump first 20 tickets across all projects
            sample_tickets = db.query(Ticket).limit(20).all()
            result["all_ticket_source_paths"] = [t.source_path for t in sample_tickets]
            logger.info(
                f"[sync] First 20 tickets across all projects:\n"
                + "\n".join(f"  [{t.status.value}] {t.source_path}" for t in sample_tickets)
            )

        # ── Improved ticket lookup strategy ──
        # Try multiple strategies to find the correct ticket
        ticket = None
        
        # Strategy 1: If we have project_name, filter by project first
        if result["project_id"]:
            like_pattern = f"%#{task_id}"
            logger.info(f"[sync] Strategy 1: Querying tickets with source_path LIKE {like_pattern!r} in project {project_name}")
            ticket = (
                db.query(Ticket)
                .filter(Ticket.source_path.like(like_pattern))
                .filter(Ticket.project_id == project.id)
                .first()
            )
            if ticket:
                logger.info(f"[sync] Strategy 1 SUCCESS: Found ticket in project {project_name}")
        
        # Strategy 2: If no project or not found, try to find by file path similarity
        if not ticket:
            current_task_file_dir = _get_current_task_file_path().parent.parent  # Go up to project root
            current_project_path = str(current_task_file_dir)
            logger.info(f"[sync] Strategy 2: Looking for tickets with source_path containing {current_project_path}")
            
            like_pattern = f"%#{task_id}"
            all_matching_tickets = db.query(Ticket).filter(Ticket.source_path.like(like_pattern)).all()
            logger.info(f"[sync] Found {len(all_matching_tickets)} tickets matching #{task_id}")
            
            for candidate in all_matching_tickets:
                logger.info(f"[sync] Checking candidate: {candidate.source_path}")
                if current_project_path.replace("\\", "/") in candidate.source_path.replace("\\", "/"):
                    ticket = candidate
                    logger.info(f"[sync] Strategy 2 SUCCESS: Found ticket by path matching")
                    break
        
        # Strategy 3: Fallback to global search (original behavior)
        if not ticket:
            like_pattern = f"%#{task_id}"
            logger.info(f"[sync] Strategy 3 (fallback): Global search with source_path LIKE {like_pattern!r}")
            ticket = db.query(Ticket).filter(Ticket.source_path.like(like_pattern)).first()
            if ticket:
                logger.info(f"[sync] Strategy 3: Found ticket globally (may be wrong project)")
                logger.warning(f"[sync] Using ticket from different project: {ticket.source_path}")

        if not ticket:
            result["error"] = f"No ticket matched LIKE pattern {like_pattern!r}"
            logger.error(
                f"[sync] ABORT — no ticket found matching source_path LIKE {like_pattern!r}\n"
                f"        Hint: check that tasks.md was ingested for project {project_name!r}"
            )
            return result

        result["ticket_found"] = True
        result["ticket_id"] = str(ticket.id)
        result["ticket_current_status"] = ticket.status.value
        logger.info(
            f"[sync] Ticket found: id={ticket.id} title={ticket.title!r} "
            f"status={ticket.status.value!r} source_path={ticket.source_path!r}"
        )

        # ── Status update ───────────────────────────────────────────────────
        try:
            target = TicketStatus(raw_status)
        except ValueError:
            logger.warning(
                f"[sync] Unrecognised status {raw_status!r}, defaulting to in_progress"
            )
            target = TicketStatus.in_progress

        result["target_status"] = target.value

        if ticket.status == target:
            result["action"] = "no_change"
            logger.info(
                f"[sync] Ticket {task_id} is already {target.value} — nothing to do."
            )
        else:
            logger.info(
                f"[sync] Updating ticket {task_id}: "
                f"{ticket.status.value!r} → {target.value!r}"
            )
            update_ticket_status(db, str(ticket.id), target.value, AuthorType.agent)
            result["action"] = f"{ticket.status.value} -> {target.value}"
            logger.info(f"[sync] ✅ Ticket {task_id} updated to {target.value}")

    except Exception as e:
        result["error"] = str(e)
        logger.exception(f"[sync] Unexpected exception: {e}")
    finally:
        db.close()

    logger.info("=" * 60)
    return result


async def _watch_current_task_file():
    """
    Background task: watches .task_runtime/ with watchfiles and syncs on every change.
    """
    from watchfiles import awatch

    logger.info("[watcher] Starting — performing initial sync on startup…")
    _sync_current_task_to_db()

    current_task_file = _get_current_task_file_path()
    watch_path = current_task_file.parent
    logger.info(f"[watcher] Now watching directory: {watch_path}")

    try:
        async for changes in awatch(str(watch_path)):
            logger.info(f"[watcher] Raw change event: {changes}")
            for change_type, changed_path in changes:
                logger.info(
                    f"[watcher] Change detected — type={change_type} path={changed_path}"
                )
                if Path(changed_path).name == "current-task.json":
                    logger.info("[watcher] current-task.json changed — triggering sync…")
                    _sync_current_task_to_db()
                else:
                    logger.info(
                        f"[watcher] Ignoring change to {Path(changed_path).name}"
                    )
    except asyncio.CancelledError:
        logger.info("[watcher] Watcher task cancelled — shutting down.")
        raise
    except Exception as e:
        logger.exception(f"[watcher] Unexpected error in watcher loop: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("[lifespan] Server starting — launching file watcher…")
    watcher_task = asyncio.create_task(_watch_current_task_file())
    yield
    logger.info("[lifespan] Server shutting down — cancelling watcher…")
    watcher_task.cancel()
    try:
        await watcher_task
    except asyncio.CancelledError:
        pass


# 2. Initialisation UNIQUE de FastAPI
app = FastAPI(
    title="Spec Kit Extension - AgentDocx API",
    version="1.0.0",
    description="API FastAPI d'orchestration Multi-Agents LangGraph pour Spec Kit",
    lifespan=lifespan,
)

# 3. Configuration CORS (Indispensable pour autoriser React sur http://localhost:3000 ou 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Inclusion du Router Pipeline 
# -> Prefix /api/v1/docs : Requis par le Frontend React (AddDocument.jsx & Documents.jsx)
app.include_router(pipeline.router, prefix="/api/v1/docs", tags=["Documents & Pipeline Frontend"])

# -> Prefix /api/v1/pipeline : Conservé pour vos scripts CLI, Watcher ou outils externes
app.include_router(pipeline.router, prefix="/api/v1/pipeline", tags=["Pipeline CLI"])

# -> Prefix /api/v1 : Endpoints Kanban (tickets, progress, ingest, commit-refine)
app.include_router(tickets.router, prefix="/api/v1", tags=["Tickets Kanban"])


# 5. Endpoints de santé (Health Checks)
@app.get("/", tags=["Health"])
async def root():
    return {
        "message": "SpecKit Extension API is running!", 
        "swagger_docs": "/docs"
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/debug-current-task", tags=["Debug"])
async def debug_current_task():
    """
    GET /debug-current-task
    Runs the full sync logic and returns a detailed diagnostic dict showing
    exactly what happened at every step (file read, project lookup, ticket match,
    status update). Use this to diagnose why the ticket isn't being updated.
    """
    from app.config import settings
    from app.utils.path_builder import BASE_DIR
    
    result = _sync_current_task_to_db()
    
    # Add additional debug info about paths
    result["debug_paths"] = {
        "BASE_DIR": str(BASE_DIR),
        "TARGET_PROJECT_PATH_setting": settings.TARGET_PROJECT_PATH,
        "computed_current_task_file": str(_get_current_task_file_path()),
    }
    
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
# import os
# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware

# from app.config import settings
# from app.database import engine, Base


# import app.models  

# # Import du router pipeline (qui contient la logique BDD & LangGraph)
# from app.api.v1.endpoints import pipeline

# # 1. Création automatique des tables BDD si elles n'existent pas
# Base.metadata.create_all(bind=engine)


# # 3. Initialisation UNIQUE de FastAPI
# app = FastAPI(
#     title="Spec Kit Extension - AgentDocx API",
#     version="1.0.0",
#     description="API FastAPI d'orchestration Multi-Agents LangGraph pour Spec Kit"
# )

# # 4. Configuration CORS
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # 5. Inclusion du Router Pipeline (Incorpore /status, /run et la BDD)
# app.include_router(pipeline.router, prefix="/api/v1/pipeline", tags=["Pipeline"])


# # 6. Endpoints de santé (Health Checks)
# @app.get("/", tags=["Health"])
# async def root():
#     return {
#         "message": "SpecKit Extension API is running!", 
#         "docs_url": "/docs"
#     }


# @app.get("/health", tags=["Health"])
# async def health():
#     return {"status": "ok", "version": "1.0.0"}


# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
