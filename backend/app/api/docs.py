import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.database import get_db
from app.models import Artifact, ArtifactType, DocVersion, PipelineRun, Project
from app.schemas import (
    DocVersionResponse,
    ParseRequest,
    ParseResponse,
    PipelineRunResponse,
)
from app.agents.pipeline import run_parsing_stage

router = APIRouter(prefix="/docs", tags=["documentation"])


def infer_artifact_type(source_path: str) -> ArtifactType:
    """Infer artifact type from a markdown filename/path."""
    filename = os.path.basename(source_path).lower()
    if filename.endswith(".md"):
        filename = filename[:-3]

    if filename in ("task", "tasks"):
        return ArtifactType.task
    if filename == "plan":
        return ArtifactType.plan
    if filename in ("spec", "specification"):
        return ArtifactType.spec
    if filename == "constitution":
        return ArtifactType.constitution
    if filename in ("contract", "contracts"):
        return ArtifactType.contract
    if filename in ("requirements", "requirement"):
        return ArtifactType.requirements
    return ArtifactType.spec


def resolve_file_path(requested_path: str) -> Path:
    """
    Resolve a file path that could be:
    - Absolute path
    - Relative to project root (parent of backend/)
    - Relative to backend/ (where server runs from)

    Returns the resolved Path if found, None otherwise.
    """
    # Get directories
    backend_dir = Path(__file__).resolve().parent.parent.parent  # -> backend/
    project_root = backend_dir.parent  # -> project root/

    # Try multiple path resolutions
    candidates = [
        Path(requested_path),  # absolute or current working dir
        project_root / requested_path,  # relative to project root
        backend_dir / requested_path,  # relative to backend
    ]

    # Normalize Windows paths (handle both / and \\)
    for candidate in candidates:
        candidate = Path(str(candidate).replace('/', os.sep).replace('\\\\', os.sep))
        if candidate.exists():
            return candidate.resolve()

    return None


@router.post("/parse", response_model=ParseResponse)
async def parse_markdown(request: ParseRequest, db: Session = Depends(get_db)):
    """
    Parse a markdown file using the Parsing Agent.

    Body: {"file_path": "specs/main/spec.md"} or {"file_path": "../specs/main/spec.md"}

    Returns structured JSON and saves PipelineRun to DB.
    """
    # 1. Resolve file path
    file_path = resolve_file_path(request.file_path)

    if not file_path:
        backend_dir = Path(__file__).resolve().parent.parent.parent
        project_root = backend_dir.parent
        raise HTTPException(
            status_code=404, 
            detail=f"File not found: {request.file_path}. Searched in: cwd={os.getcwd()}, project_root={project_root}"
        )

    # Store the relative path for the database (from project root)
    backend_dir = Path(__file__).resolve().parent.parent.parent
    project_root = backend_dir.parent
    try:
        db_source_path = str(file_path.relative_to(project_root)).replace(os.sep, '/')
    except ValueError:
        db_source_path = str(file_path).replace(os.sep, '/')

    # 2. Find or create Artifact
    artifact = db.query(Artifact).filter(Artifact.source_path == db_source_path).first()

    if not artifact:
        # Need a project first
        project = db.query(Project).first()
        if not project:
            project = Project(name="Default Project")
            db.add(project)
            db.commit()
            db.refresh(project)

        artifact = Artifact(
            project_id=project.id,
            source_path=db_source_path,
            artifact_type=infer_artifact_type(db_source_path),
        )
        db.add(artifact)
        db.commit()
        db.refresh(artifact)

    # 3. Run parsing pipeline (pass the actual file path for reading)
    try:
        pipeline_run = await run_parsing_stage(db, artifact, str(file_path))
    except Exception as e:
        # Surface parsing errors as HTTP 500 with helpful detail for debugging
        raise HTTPException(status_code=500, detail=f"Parsing failed: {e}")

    # 4. Return result
    return ParseResponse(
        success=True,
        source_path=db_source_path,
        structured_json=pipeline_run.structured_json,
        pipeline_run_id=pipeline_run.id,
    )


@router.get("/pipeline-run/{run_id}", response_model=PipelineRunResponse)
async def get_pipeline_run(run_id: UUID, db: Session = Depends(get_db)):
    """Get a pipeline run by ID to check status and output."""
    run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    return run


@router.get("/artifact/{artifact_id}/versions", response_model=List[DocVersionResponse])
async def list_doc_versions(artifact_id: UUID, db: Session = Depends(get_db)):
    """List all PDF versions for an artifact."""
    versions = (
        db.query(DocVersion)
        .filter(DocVersion.artifact_id == artifact_id)
        .order_by(DocVersion.version_no.desc())
        .all()
    )
    return versions