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


def _sync_copilot_instructions() -> None:
    """
    Write the canonical .github/copilot-instructions.md (source of truth lives
    at the repo root, next to this backend) into the watched child project
    (TARGET_PROJECT_PATH), every time the backend starts.

    This exists independently of the VS Code extension's own copy-on-activate
    logic: the extension only copies from *its own installed package*, which
    may be a stale/prebuilt .vsix that never bundled .github/. The backend,
    by contrast, always runs from this exact source tree, so it can guarantee
    the child project gets the current instructions on every restart —
    regardless of what .vsix happens to be installed.
    """
    from app.utils.path_builder import BASE_DIR

    if not settings.TARGET_PROJECT_PATH:
        logger.info("[copilot-instructions] TARGET_PROJECT_PATH not set — skipping sync.")
        return

    source = BASE_DIR / ".github" / "copilot-instructions.md"
    if not source.exists():
        logger.warning(f"[copilot-instructions] Source file not found: {source}")
        return

    target_dir = Path(settings.TARGET_PROJECT_PATH) / ".github"
    target = target_dir / "copilot-instructions.md"

    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        content = source.read_text(encoding="utf-8")
        target.write_text(content, encoding="utf-8")
        logger.info(f"[copilot-instructions] Synced {source} -> {target}")
    except OSError as e:
        logger.error(f"[copilot-instructions] Failed to sync: {e}")


def _find_ticket_for_task(db, project, project_name: str, task_id: str):
    """
    Locate the ticket matching task_id using a 3-strategy fallback:
    project-scoped match -> path-similarity match -> global match.
    """
    from app.models import Ticket

    like_pattern = f"%#{task_id}"

    # Strategy 1: project-scoped
    if project:
        ticket = (
            db.query(Ticket)
            .filter(Ticket.source_file_path.like(like_pattern))
            .filter(Ticket.project_id == project.id)
            .first()
        )
        if ticket:
            return ticket

    # Strategy 2: path-similarity match against the watched project root
    current_task_file_dir = _get_current_task_file_path().parent.parent
    current_project_path = str(current_task_file_dir).replace("\\", "/")
    all_matching_tickets = db.query(Ticket).filter(Ticket.source_file_path.like(like_pattern)).all()
    for candidate in all_matching_tickets:
        if current_project_path in candidate.source_file_path.replace("\\", "/"):
            return candidate

    # Strategy 3: global fallback (may be wrong project, but better than nothing)
    return db.query(Ticket).filter(Ticket.source_file_path.like(like_pattern)).first()


def _sync_current_task_to_db() -> dict:
    """
    Read current-task.json and update ticket statuses in the DB.

    Two things are synced:
    • The single `task_id`/`status` pair (legacy / "what Copilot is doing right now").
    • The full `tasks` map, if present — every task_id -> status entry it contains
      is applied too. This is what lets status recover even if the backend wasn't
      running to catch every individual in_progress/done transition live.

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
        "bulk_sync": [],
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
            result["all_ticket_source_paths"] = [t.source_file_path for t in sample_tickets]
            logger.info(
                f"[sync] Tickets in project ({len(sample_tickets)} total), source_paths:\n"
                + "\n".join(f"  [{t.status.value}] {t.source_file_path}" for t in sample_tickets)
            )
        else:
            # No project filter — dump first 20 tickets across all projects
            sample_tickets = db.query(Ticket).limit(20).all()
            result["all_ticket_source_paths"] = [t.source_file_path for t in sample_tickets]
            logger.info(
                f"[sync] First 20 tickets across all projects:\n"
                + "\n".join(f"  [{t.status.value}] {t.source_file_path}" for t in sample_tickets)
            )

        # ── Ticket lookup (3-strategy fallback) ─────────────────────────────
        ticket = _find_ticket_for_task(db, project if result["project_id"] else None, project_name, task_id)

        if not ticket:
            result["error"] = f"No ticket matched task_id {task_id!r}"
            logger.error(
                f"[sync] No ticket found matching task_id={task_id!r}\n"
                f"        Hint: check that tasks.md was ingested for project {project_name!r}"
            )
        else:
            result["ticket_found"] = True
            result["ticket_id"] = str(ticket.id)
            result["ticket_current_status"] = ticket.status.value
            logger.info(
                f"[sync] Ticket found: id={ticket.id} title={ticket.title!r} "
                f"status={ticket.status.value!r} source_file_path={ticket.source_file_path!r}"
            )

            # ── Status update ────────────────────────────────────────────────
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

        # ── Bulk sync from the full `tasks` status map, if present ─────────
        # This is what lets status recover even when the backend missed live
        # transitions (e.g. wasn't running while Copilot worked through tasks).
        tasks_map = data.get("tasks")
        if isinstance(tasks_map, dict):
            logger.info(f"[sync] Bulk-syncing {len(tasks_map)} task(s) from `tasks` map…")
            for map_task_id, map_status in tasks_map.items():
                entry = {"task_id": map_task_id, "status": map_status}
                try:
                    map_target = TicketStatus(map_status)
                except ValueError:
                    entry["error"] = f"Unrecognised status {map_status!r}"
                    logger.warning(f"[sync] Bulk: skipping {map_task_id} — {entry['error']}")
                    result["bulk_sync"].append(entry)
                    continue

                map_ticket = _find_ticket_for_task(
                    db, project if result["project_id"] else None, project_name, map_task_id
                )
                if not map_ticket:
                    entry["error"] = "No matching ticket"
                    logger.warning(f"[sync] Bulk: no ticket found for {map_task_id}")
                    result["bulk_sync"].append(entry)
                    continue

                entry["ticket_id"] = str(map_ticket.id)
                if map_ticket.status == map_target:
                    entry["action"] = "no_change"
                else:
                    entry["action"] = f"{map_ticket.status.value} -> {map_target.value}"
                    update_ticket_status(db, str(map_ticket.id), map_target.value, AuthorType.agent)
                    logger.info(f"[sync] Bulk: {map_task_id} {entry['action']}")
                result["bulk_sync"].append(entry)

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
    logger.info("[lifespan] Server starting — syncing copilot-instructions.md…")
    _sync_copilot_instructions()
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
