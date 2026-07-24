import os
import threading
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from uuid import UUID

from app.database import get_db
from app.models import Artifact, ArtifactType, DocVersion, PipelineRun, Project, PipelineStage
from app.schema import (
    DocVersionResponse,
    ParseRequest,
    ParseResponse,
    PipelineRunResponse,
    DashboardRow,
    DashboardSummary,
    UploadResponse,
    DocumentRow,
)
from app.utils.diagram_pdf import generate_diagram_pdf
import logging
import traceback

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/docs", tags=["documentation"])


def infer_artifact_type(source_path: str) -> ArtifactType:
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
    backend_dir = Path(__file__).resolve().parent.parent.parent
    project_root = backend_dir.parent

    candidates = [
        Path(requested_path),
        project_root / requested_path,
        backend_dir / requested_path,
    ]

    for candidate in candidates:
        candidate = Path(str(candidate).replace('/', os.sep).replace('\\\\', os.sep))
        if candidate.exists():
            return candidate.resolve()

    return None


@router.post("/parse", response_model=ParseResponse)
async def parse_markdown(request: ParseRequest, db: Session = Depends(get_db)):
    try:
        file_path = resolve_file_path(request.file_path)
        if not file_path:
            raise HTTPException(status_code=404, detail=f"File not found: {request.file_path}")

        backend_dir = Path(__file__).resolve().parent.parent.parent
        project_root = backend_dir.parent
        try:
            db_source_path = str(file_path.relative_to(project_root)).replace(os.sep, '/')
        except ValueError:
            db_source_path = str(file_path).replace(os.sep, '/')

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
                artifact_type=infer_artifact_type(db_source_path).value,
            )
            db.add(artifact)
            db.commit()
            db.refresh(artifact)

        # Create a pipeline run for tracking
        pipeline_run = PipelineRun(artifact_id=artifact.id, current_stage=PipelineStage.parsing)
        db.add(pipeline_run)
        db.commit()
        db.refresh(pipeline_run)

        # For now, return the pipeline run ID. The actual parsing agent integration
        # would update this run with structured_json and advance the stage.
        return {
            "success": True,
            "source_path": db_source_path,
            "structured_json": {},
            "pipeline_run_id": pipeline_run.id,
        }

    except HTTPException:
        raise
    except Exception as exc:
        tb = traceback.format_exc()
        logger.error(f"parse_markdown CRASHED: {type(exc).__name__}: {exc}")
        logger.error(tb)
        raise HTTPException(status_code=500, detail={"error": type(exc).__name__, "message": str(exc)})


@router.get("/pipeline-run/{run_id}", response_model=PipelineRunResponse)
async def get_pipeline_run(run_id: UUID, db: Session = Depends(get_db)):
    run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    return run


@router.get("/artifact/{artifact_id}/versions", response_model=List[DocVersionResponse])
async def list_doc_versions(artifact_id: UUID, db: Session = Depends(get_db)):
    versions = (
        db.query(DocVersion)
        .filter(DocVersion.artifact_id == artifact_id)
        .order_by(DocVersion.version_no.desc())
        .all()
    )
    return versions


# ============================================
# DASHBOARD ENDPOINTS
# ============================================

@router.get("/dashboard", response_model=List[DashboardRow])
def get_dashboard(db: Session = Depends(get_db)):
    rows = (
        db.query(DocVersion, Artifact, Project, PipelineRun)
        .join(Artifact, DocVersion.artifact_id == Artifact.id)
        .join(Project, Artifact.project_id == Project.id)
        .outerjoin(PipelineRun, DocVersion.pipeline_run_id == PipelineRun.id)
        .order_by(DocVersion.generated_at.desc())
        .all()
    )

    result = []
    for doc_version, artifact, project, pipeline_run in rows:
        agent_running = "completed"
        current_stage = "completed"
        started_at = None

        if pipeline_run:
            current_stage = str(pipeline_run.current_stage.value if hasattr(pipeline_run.current_stage, 'value') else pipeline_run.current_stage)
            started_at = pipeline_run.started_at
            if current_stage == "failed":
                agent_running = "failed"
            elif current_stage != "completed":
                agent_running = current_stage

        result.append(DashboardRow(
            doc_version_id=doc_version.id,
            artifact_id=artifact.id,
            artifact_name=artifact.name,
            artifact_type=artifact.artifact_type,
            project_id=project.id,
            project_name=project.name,
            version_no=doc_version.version_no,
            current_stage=current_stage,
            agent_running=agent_running,
            kpi_global_score=doc_version.kpi_global_score or (pipeline_run.global_kpi if pipeline_run else None),
            pdf_path=doc_version.pdf_path,
            pdf_download_url=f"/api/v1/docs/pdf/{doc_version.id}" if doc_version.pdf_path else None,
            generated_at=doc_version.generated_at,
            started_at=started_at,
        ))

    return result


@router.get("/dashboard/summary", response_model=DashboardSummary)
def get_dashboard_summary(db: Session = Depends(get_db)):
    total_artifacts = db.query(Artifact).count()
    total_versions = db.query(DocVersion).count()
    completed_runs = db.query(PipelineRun).filter(PipelineRun.current_stage == PipelineStage.completed).count()
    failed_runs = db.query(PipelineRun).filter(PipelineRun.current_stage == PipelineStage.failed).count()
    avg_kpi = db.query(func.avg(PipelineRun.global_kpi)).filter(PipelineRun.global_kpi != None).scalar()

    return DashboardSummary(
        total_artifacts=total_artifacts,
        total_versions=total_versions,
        completed_runs=completed_runs,
        failed_runs=failed_runs,
        avg_kpi_score=round(avg_kpi, 2) if avg_kpi else None,
    )


@router.get("/pdf/{doc_version_id}")
def download_pdf(doc_version_id: UUID, db: Session = Depends(get_db)):
    from fastapi.responses import FileResponse

    doc_version = db.query(DocVersion).filter(DocVersion.id == doc_version_id).first()
    if not doc_version or not doc_version.pdf_path:
        raise HTTPException(status_code=404, detail="PDF not found")

    return FileResponse(
        path=doc_version.pdf_path,
        filename=f"{doc_version.artifact.name if doc_version.artifact else 'doc'}_v{doc_version.version_no}.pdf",
        media_type="application/pdf",
        content_disposition_type="inline",
    )


# ============================================
# FILE UPLOAD + PIPELINE TRIGGER
# ============================================

def _run_pipeline_in_background(file_path: Path, file_content: str):
    """Run the LangGraph pipeline in a background thread."""
    try:
        from app.graph.workflow import create_pipeline_workflow
        pipeline = create_pipeline_workflow()
        initial_state = {
            "file_name": file_path.name,
            "file_content": file_content,
        }
        pipeline.invoke(initial_state)
        logger.info(f"Pipeline completed for {file_path.name}")
    except Exception as exc:
        logger.error(f"Pipeline failed for {file_path.name}: {exc}")
        logger.error(traceback.format_exc())


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    projectName: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        if not file.filename.endswith(".md"):
            raise HTTPException(status_code=400, detail="Only .md files are allowed")

        backend_dir = Path(__file__).resolve().parent.parent.parent
        project_root = backend_dir.parent
        upload_dir = project_root / "test_files"
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_path = upload_dir / file.filename
        content = await file.read()
        file_path.write_bytes(content)
        file_content = content.decode("utf-8")

        project = db.query(Project).filter(Project.name == projectName).first()
        if not project:
            project = Project(name=projectName)
            db.add(project)
            db.commit()
            db.refresh(project)

        source_path = f"test_files/{file.filename}"
        artifact = db.query(Artifact).filter(Artifact.source_path == source_path).first()
        if not artifact:
            artifact = Artifact(
                project_id=project.id,
                source_path=source_path,
                artifact_type=infer_artifact_type(source_path).value,
            )
            db.add(artifact)
            db.commit()
            db.refresh(artifact)

        pipeline_run = PipelineRun(artifact_id=artifact.id, current_stage=PipelineStage.parsing)
        db.add(pipeline_run)
        db.commit()
        db.refresh(pipeline_run)

        thread = threading.Thread(
            target=_run_pipeline_in_background,
            args=(file_path, file_content),
            daemon=True,
        )
        thread.start()

        return UploadResponse(
            artifact_id=artifact.id,
            pipeline_run_id=pipeline_run.id,
            status="parsing",
            message=f"File '{file.filename}' uploaded. Pipeline started.",
        )

    except HTTPException:
        raise
    except Exception as exc:
        tb = traceback.format_exc()
        logger.error(f"upload_document CRASHED: {type(exc).__name__}: {exc}")
        logger.error(tb)
        raise HTTPException(status_code=500, detail={"error": type(exc).__name__, "message": str(exc)})


# ============================================
# DOCUMENTS LIST (for frontend DataGrid)
# ============================================

@router.get("/documents", response_model=List[DocumentRow])
def list_documents(db: Session = Depends(get_db)):
    artifacts = db.query(Artifact).order_by(Artifact.created_at.desc()).all()
    result = []

    for artifact in artifacts:
        latest_run = (
            db.query(PipelineRun)
            .filter(PipelineRun.artifact_id == artifact.id)
            .order_by(PipelineRun.started_at.desc())
            .first()
        )

        latest_version = (
            db.query(DocVersion)
            .filter(DocVersion.artifact_id == artifact.id)
            .order_by(DocVersion.version_no.desc())
            .first()
        )

        status = "pending"
        kpi = None
        pipeline_run_id = None
        doc_version_id = None
        version = "v0"

        if latest_run:
            pipeline_run_id = latest_run.id
            stage = latest_run.current_stage
            if hasattr(stage, "value"):
                stage = stage.value
            status = stage
            kpi = latest_run.global_kpi

        if latest_version:
            doc_version_id = latest_version.id
            version = f"v{latest_version.version_no}"
            if latest_version.kpi_global_score:
                kpi = latest_version.kpi_global_score

        result.append(DocumentRow(
            id=artifact.id,
            name=artifact.name,
            projectName=artifact.project.name if artifact.project else "Unknown",
            version=version,
            status=status,
            kpi=round(kpi, 1) if kpi else None,
            doc_version_id=doc_version_id,
            pipeline_run_id=pipeline_run_id,
        ))

    return result