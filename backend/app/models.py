import uuid
import enum

from sqlalchemy import (
    Column,
    String,
    Integer,
    Text,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Enum as SAEnum,
    Float,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


# ============================================
# ENUMS
# ============================================

class ArtifactType(str, enum.Enum):
    spec = "spec"
    plan = "plan"
    task = "task"
    constitution = "constitution"
    contract = "contract"
    requirements = "requirements"


class GeneratedBy(str, enum.Enum):
    agent = "agent"
    user = "user"


class PipelineStage(str, enum.Enum):
    parsing = "parsing"
    parallel_enrichment = "parallel_enrichment"
    writing = "writing"
    layout = "layout"
    rendering = "rendering"
    completed = "completed"
    failed = "failed"


# ============================================
# Project
# ============================================

class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name = Column(String(255), nullable=False)
    repo_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    artifacts = relationship(
        "Artifact", back_populates="project", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Project id={self.id} name={self.name!r}>"


# ============================================
# Artifact
# ============================================

class Artifact(Base):
    __tablename__ = "artifacts"
    __table_args__ = (
        UniqueConstraint("project_id", "source_path", name="uq_artifact_project_path"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    project_id = Column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    current_file_hash = Column(String(64), nullable=True)
    source_path = Column(String(500), nullable=False)
    artifact_type = Column(String(100), nullable=False, default="unknown")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    project = relationship("Project", back_populates="artifacts")
    doc_versions = relationship(
        "DocVersion",
        back_populates="artifact",
        cascade="all, delete-orphan",
        order_by="DocVersion.version_no",
    )
    pipeline_runs = relationship(
        "PipelineRun",
        back_populates="artifact",
        cascade="all, delete-orphan",
        order_by="PipelineRun.started_at",
    )

    @property
    def name(self) -> str:
        from pathlib import Path
        return Path(self.source_path).stem

    def __repr__(self) -> str:
        return f"<Artifact id={self.id} source_path={self.source_path!r}>"


# ============================================
# DocVersion — stores the final PDF
# ============================================

class DocVersion(Base):
    __tablename__ = "doc_versions"
    __table_args__ = (
        UniqueConstraint("artifact_id", "version_no", name="uq_docversion_artifact_versionno"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    artifact_id = Column(
        UUID(as_uuid=True), ForeignKey("artifacts.id", ondelete="CASCADE"), nullable=False
    )
    version_no = Column(Integer, nullable=False)
    pdf_path = Column(String(500), nullable=False)
    source_file_hash = Column(String(64), nullable=True)
    generated_at = Column(DateTime, server_default=func.now(), nullable=False)
    commit_hash = Column(String(40), nullable=True)
    generated_by = Column(
        SAEnum(GeneratedBy, name="generated_by_enum", native_enum=False),
        nullable=False,
        default=GeneratedBy.agent,
    )
    # KPI global score (0-100) for dashboard
    kpi_global_score = Column(Float, nullable=True)
    # Link to the pipeline run that produced this version
    pipeline_run_id = Column(
        UUID(as_uuid=True), ForeignKey("pipeline_runs.id", ondelete="SET NULL"), nullable=True
    )

    artifact = relationship("Artifact", back_populates="doc_versions")
    pipeline_run = relationship("PipelineRun", back_populates="doc_version")

    @property
    def project_name(self) -> str:
        return self.artifact.project.name if self.artifact and self.artifact.project else "Unknown"

    @property
    def artifact_name(self) -> str:
        return self.artifact.name if self.artifact else "Unknown"

    def __repr__(self) -> str:
        return f"<DocVersion id={self.id} v{self.version_no} artifact_id={self.artifact_id}>"


# ============================================
# PipelineRun — KPI scores ONLY, no agent outputs
# ============================================

class PipelineRun(Base):
    """
    Stores ONLY KPI scores from each agent stage.
    NO agent outputs (structured_json, summary_output, etc.) are stored here.
    Those stay in memory/filesystem during pipeline execution.
    """
    __tablename__ = "pipeline_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    artifact_id = Column(
        UUID(as_uuid=True), ForeignKey("artifacts.id", ondelete="CASCADE"), nullable=False
    )

    current_stage = Column(
        SAEnum(PipelineStage, name="pipeline_stage_enum", native_enum=False),
        nullable=False,
        default=PipelineStage.parsing,
    )

    # --- KPI scores only (0-100) ---
    parsing_kpi = Column(Float, nullable=True)
    summary_kpi = Column(Float, nullable=True)
    diagram_kpi = Column(Float, nullable=True)
    glossary_kpi = Column(Float, nullable=True)
    doc_writer_kpi = Column(Float, nullable=True)
    layout_kpi = Column(Float, nullable=True)
    global_kpi = Column(Float, nullable=True)  # weighted average of all stages

    started_at = Column(DateTime, server_default=func.now(), nullable=False)

    artifact = relationship("Artifact", back_populates="pipeline_runs")
    doc_version = relationship("DocVersion", back_populates="pipeline_run", uselist=False)

    def __repr__(self) -> str:
        return f"<PipelineRun id={self.id} stage={self.current_stage} kpi={self.global_kpi}>"