from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List, Any
from uuid import UUID

from app.models import ArtifactType, GeneratedBy, PipelineStage


# --- Project ---
class ProjectBase(BaseModel):
    name: str
    repo_url: Optional[str] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectResponse(ProjectBase):
    id: UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- Artifact ---
class ArtifactBase(BaseModel):
    source_path: str
    artifact_type: str  # Use str to avoid enum serialization issues

class ArtifactCreate(ArtifactBase):
    project_id: UUID

class ArtifactResponse(ArtifactBase):
    id: UUID
    project_id: UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- DocVersion ---
class DocVersionBase(BaseModel):
    version_no: int
    pdf_path: str
    commit_hash: Optional[str] = None
    generated_by: str = "agent"

class DocVersionCreate(DocVersionBase):
    artifact_id: UUID

class DocVersionResponse(DocVersionBase):
    id: UUID
    artifact_id: UUID
    generated_at: datetime
    pipeline_run_id: Optional[UUID] = None
    kpi_global_score: Optional[float] = None
    model_config = ConfigDict(from_attributes=True)


# --- PipelineRun ---
class PipelineRunBase(BaseModel):
    current_stage: str = "parsing"
    structured_json: Optional[dict] = None
    summary_output: Optional[str] = None
    diagram_output: Optional[dict] = None
    glossary_output: Optional[dict] = None
    written_doc: Optional[str] = None
    layout_output: Optional[str] = None
   

class PipelineRunCreate(PipelineRunBase):
    artifact_id: UUID

class PipelineRunResponse(PipelineRunBase):
    id: UUID
    artifact_id: UUID
    started_at: datetime
    completed_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


# --- Parse Request/Response ---
class ParseRequest(BaseModel):
    file_path: str

class ParseResponse(BaseModel):
    success: bool
    source_path: str
    structured_json: Any
    pipeline_run_id: UUID


# ============================================
# DASHBOARD SCHEMAS
# ============================================

class DashboardRow(BaseModel):
    doc_version_id: UUID
    artifact_id: UUID
    artifact_name: str
    artifact_type: str
    project_id: UUID
    project_name: str
    version_no: int
    current_stage: str
    agent_running: str
    kpi_global_score: Optional[float] = None
    pdf_path: Optional[str] = None
    pdf_download_url: Optional[str] = None
    generated_at: datetime
    started_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class DashboardSummary(BaseModel):
    total_artifacts: int
    total_versions: int
    completed_runs: int
    failed_runs: int
    avg_kpi_score: Optional[float] = None
    model_config = ConfigDict(from_attributes=True)


# ============================================
# UPLOAD & DOCUMENTS LIST SCHEMAS
# ============================================

class UploadResponse(BaseModel):
    artifact_id: UUID
    pipeline_run_id: UUID
    status: str
    message: str


class DocumentRow(BaseModel):
    id: UUID
    name: str
    projectName: str
    version: str
    status: str
    kpi: Optional[float] = None
    doc_version_id: Optional[UUID] = None
    pipeline_run_id: Optional[UUID] = None