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
    artifact_type: ArtifactType

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
    generated_by: GeneratedBy = GeneratedBy.agent

class DocVersionCreate(DocVersionBase):
    artifact_id: UUID

class DocVersionResponse(DocVersionBase):
    id: UUID
    artifact_id: UUID
    generated_at: datetime
    pipeline_run_id: Optional[UUID] = None
    model_config = ConfigDict(from_attributes=True)


# --- PipelineRun ---
class PipelineRunBase(BaseModel):
    current_stage: PipelineStage = PipelineStage.parsing
    structured_json: Optional[dict] = None
    summary_output: Optional[str] = None
    diagram_output: Optional[dict] = None
    glossary_output: Optional[dict] = None
    written_doc: Optional[str] = None
    layout_output: Optional[str] = None
    error_message: Optional[str] = None

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
    structured_json: dict
    pipeline_run_id: UUID