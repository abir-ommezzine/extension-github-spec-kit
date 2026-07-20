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
from app.utils.diagram_pdf import generate_diagram_pdf
from app.agents.pipeline import run_parsing_stage
from app.agents.pipeline import run_diagram_stage
from app.models import PipelineRun, PipelineStage
import logging
import traceback

logger = logging.getLogger(__name__)

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
    """
    try:
        # 1. Resolve file path
        file_path = resolve_file_path(request.file_path)

        if not file_path:
            backend_dir = Path(__file__).resolve().parent.parent.parent
            project_root = backend_dir.parent
            raise HTTPException(
                status_code=404,
                detail=f"File not found: {request.file_path}. Searched in: cwd={os.getcwd()}, project_root={project_root}"
            )

        # Store the relative path for the database
        backend_dir = Path(__file__).resolve().parent.parent.parent
        project_root = backend_dir.parent
        try:
            db_source_path = str(file_path.relative_to(project_root)).replace(os.sep, '/')
        except ValueError:
            db_source_path = str(file_path).replace(os.sep, '/')

        # 2. Find or create Artifact
        artifact = db.query(Artifact).filter(Artifact.source_path == db_source_path).first()

        if not artifact:
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

        # 3. Run parsing stage — returns PipelineRun object
        pipeline_run = await run_parsing_stage(db, artifact, file_path)

        # UPDATE artifact_type from LLM-detected type
        structured = pipeline_run.structured_json or {}
        detected_type = structured.get("document_type", "unknown") if isinstance(structured, dict) else "unknown"
        if detected_type and detected_type != artifact.artifact_type:
            artifact.artifact_type = detected_type
            db.commit()
            db.refresh(artifact)

        # Return ONLY parsing results — no diagram generation
        return {
            "success": pipeline_run.current_stage.value != "failed",
            "source_path": db_source_path,
            "structured_json": pipeline_run.structured_json or {},
            "pipeline_run_id": pipeline_run.id,
        }

    except HTTPException:
        raise

    except Exception as exc:
        tb = traceback.format_exc()
        logger.error("=" * 70)
        logger.error(f"parse_markdown CRASHED: {type(exc).__name__}: {exc}")
        logger.error(tb)
        logger.error("=" * 70)
        raise HTTPException(
            status_code=500,
            detail={
                "error": type(exc).__name__,
                "message": str(exc),
                "traceback": tb,
            }
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

@router.post("/pipeline-run/{run_id}/diagrams")
async def generate_diagrams_for_run(run_id: str, db: Session = Depends(get_db)):
    """
    Trigger the Diagram Agent for an existing pipeline run,
    then generate a PDF containing all diagrams.
    """
    try:
        pipeline_run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
        if not pipeline_run:
            raise HTTPException(status_code=404, detail="Pipeline run not found")

        if not pipeline_run.structured_json:
            raise HTTPException(
                status_code=400,
                detail="Pipeline run has no structured_json. Run parsing first."
            )

        # FORCE REGENERATION: clear old diagram output
        pipeline_run.diagram_output = None
        db.commit()

        # 1. Generate diagrams via LLM (force=True)
        await run_diagram_stage(db, pipeline_run, force=True)

        # 2. Generate PDF from diagrams
        pdf_path = None
        doc_version = None

        if pipeline_run.diagram_output and pipeline_run.diagram_output.get("diagrams"):
            try:
                pdf_path = await generate_diagram_pdf(
                    str(pipeline_run.artifact_id),
                    pipeline_run.diagram_output
                )

                # 3. Create DocVersion record
                version_no = (
                    db.query(DocVersion)
                    .filter(DocVersion.artifact_id == pipeline_run.artifact_id)
                    .count()
                    + 1
                )

                doc_version = DocVersion(
                    artifact_id=pipeline_run.artifact_id,
                    version_no=version_no,
                    pdf_path=pdf_path,
                    pipeline_run_id=pipeline_run.id,
                )
                db.add(doc_version)
                db.commit()

            except Exception as pdf_exc:
                pdf_path = None
                doc_version = None
                pdf_error = f"PDF generation failed: {pdf_exc}"
                print(f"[DIAGRAM PDF ERROR] {pdf_error}")
                print(traceback.format_exc())
        else:
            pdf_error = "No diagram output from LLM"

        return {
            "pipeline_run_id": str(pipeline_run.id),
            "current_stage": pipeline_run.current_stage.value,
            "diagrams": pipeline_run.diagram_output or {},
            "pdf_path": pdf_path,
            "pdf_error": pdf_error if pdf_path is None else None,
            "doc_version_id": str(doc_version.id) if doc_version else None,
        }

    except HTTPException:
        raise

    except Exception as exc:
        tb = traceback.format_exc()
        print("=" * 70)
        print(f"DIAGRAM ENDPOINT CRASHED: {type(exc).__name__}: {exc}")
        print(tb)
        print("=" * 70)
        raise HTTPException(
            status_code=500,
            detail={
                "error": type(exc).__name__,
                "message": str(exc),
                "traceback": tb,
            }
        )