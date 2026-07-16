
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


class GeneratedBy(str, enum.Enum):
    agent = "agent"
    user = "user"


class PipelineStage(str, enum.Enum):
    """Étape courante du pipeline — utile pour un dashboard de suivi en temps réel."""
    parsing = "parsing"
    parallel_enrichment = "parallel_enrichment"   # Summary / Diagram / Glossary
    writing = "writing"                            # Documentation Writer
    layout = "layout"                               # Design/Layout Agent
    rendering = "rendering"                         # Markdown/HTML -> PDF Generator
    completed = "completed"
    failed = "failed"


# ============================================
# Project / Artifact / DocVersion
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


class Artifact(Base):
    __tablename__ = "artifacts"
    __table_args__ = (
        UniqueConstraint("project_id", "source_path", name="uq_artifact_project_path"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    project_id = Column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    source_path = Column(String(500), nullable=False)  # ex: specs/003-x/context.md
    artifact_type = Column(SAEnum(ArtifactType, name="artifact_type_enum"), nullable=False)
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

    def __repr__(self) -> str:
        return f"<Artifact id={self.id} source_path={self.source_path!r}>"


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
    generated_at = Column(DateTime, server_default=func.now(), nullable=False)
    commit_hash = Column(String(40), nullable=True)
    generated_by = Column(
        SAEnum(GeneratedBy, name="generated_by_enum"),
        nullable=False,
        default=GeneratedBy.agent,
    )
    # Rattache cette version à l'exécution de pipeline qui l'a produite
    pipeline_run_id = Column(
        UUID(as_uuid=True), ForeignKey("pipeline_runs.id", ondelete="SET NULL"), nullable=True
    )

    artifact = relationship("Artifact", back_populates="doc_versions")
    pipeline_run = relationship("PipelineRun", back_populates="doc_version")

    def __repr__(self) -> str:
        return f"<DocVersion id={self.id} v{self.version_no} artifact_id={self.artifact_id}>"


# ============================================
# PipelineRun — suivi/monitoring du pipeline d'agents
# ============================================

class PipelineRun(Base):
    """
    Une ligne = une exécution complète du pipeline pour un artifact donné.
    Chaque colonne de sortie correspond à une étape du schéma :
    Parsing -> (Summary | Diagram | Glossary) -> Writer -> Layout -> PDF.

    Permet de :
      - visualiser la progression en cours (current_stage) sur le dashboard,
      - déboguer une étape précise sans relancer tout le pipeline,
      - respecter l'AC "output must not silently drop requirements" en
        conservant le JSON structuré source de vérité entre les étapes.
    """
    __tablename__ = "pipeline_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    artifact_id = Column(
        UUID(as_uuid=True), ForeignKey("artifacts.id", ondelete="CASCADE"), nullable=False
    )

    current_stage = Column(
        SAEnum(PipelineStage, name="pipeline_stage_enum"),
        nullable=False,
        default=PipelineStage.parsing,
    )

    # --- Sorties de chaque étape (nullable : remplies au fur et à mesure) ---
    structured_json = Column(JSONB, nullable=True)      # sortie du Parsing Agent
    summary_output = Column(Text, nullable=True)          # sortie du Summary Agent
    diagram_output = Column(JSONB, nullable=True)         # sortie du Diagram Agent
    glossary_output = Column(JSONB, nullable=True)        # sortie du Glossary Agent
    written_doc = Column(Text, nullable=True)              # sortie du Documentation Writer
    layout_output = Column(Text, nullable=True)            # sortie du Design/Layout Agent (MD/HTML final)

    error_message = Column(Text, nullable=True)            # renseigné si current_stage = failed

    started_at = Column(DateTime, server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    artifact = relationship("Artifact", back_populates="pipeline_runs")
    doc_version = relationship("DocVersion", back_populates="pipeline_run", uselist=False)

    def __repr__(self) -> str:
        return f"<PipelineRun id={self.id} stage={self.current_stage} artifact_id={self.artifact_id}>"