import uuid
import enum

from sqlalchemy import (
    Column,
    String,
    Integer,
    Text,
    DateTime,
    Float,
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
    tasks = "tasks"
    constitution = "constitution"
    requirements = "requirements"
    contracts = "contracts"
    checklist = "checklist"


class GeneratedBy(str, enum.Enum):
    agent = "agent"
    user = "user"


class PipelineStage(str, enum.Enum):
    parsing = "parsing"
    summary = "summary"
    glossary = "glossary"
    diagram = "diagram"
    writing = "writing"
    layout = "layout"
    rendering = "rendering"
    completed = "completed"
    failed = "failed"


class TicketStatus(str, enum.Enum):
    todo = "todo"
    in_progress = "in_progress"
    done = "done"


class AuthorType(str, enum.Enum):
    human = "human"
    agent = "agent"


class TicketEventType(str, enum.Enum):
    status_change = "status_change"
    status_override = "status_override"
    comment_added = "comment_added"
    doc_regenerated = "doc_regenerated"


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
    current_file_hash = Column(String(64), nullable=True)
    source_path = Column(String(500), nullable=False)
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


# Dans app/models.py (classe DocVersion)

class DocVersion(Base):
    __tablename__ = "doc_versions"
    __table_args__ = (
        UniqueConstraint("artifact_id", "version_no", name="uq_docversion_artifact_versionno"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    artifact_id = Column(
        UUID(as_uuid=True), ForeignKey("artifacts.id", ondelete="CASCADE"), nullable=False
    )
    
    # Numéro séquentiel interne (1, 2, 3...)
    version_no = Column(Integer, nullable=False)
    
    # Label affiché (ex: "1.0", "2.0")
    version_label = Column(String(20), nullable=False, default="1.0")
    
    pdf_path = Column(String(500), nullable=False)
    source_file_hash = Column(String(64), nullable=False)
    generated_at = Column(DateTime, server_default=func.now(), nullable=False)
    sections_summary = Column(JSONB, nullable=True)
    commit_hash = Column(String(40), nullable=True)
    generated_by = Column(
        SAEnum(GeneratedBy, name="generated_by_enum"),
        nullable=False,
        default=GeneratedBy.agent,
    )
    pipeline_run_id = Column(
        UUID(as_uuid=True), ForeignKey("pipeline_runs.id", ondelete="SET NULL"), nullable=True
    )

    global_kpi_score = Column(Float, nullable=True)

    artifact = relationship("Artifact", back_populates="doc_versions")
    pipeline_run = relationship("PipelineRun", back_populates="doc_version")

    def __repr__(self) -> str:
        return f"<DocVersion id={self.id} v{self.version_label} artifact_id={self.artifact_id}>"

# ============================================
# PipelineRun — Suivi complet & Évaluations BDD + Outputs
# ============================================

class PipelineRun(Base):
    """
    Une ligne = une exécution complète du pipeline.
    Stocke les résultats bruts + les JSONs d'évaluation pour les 6 agents.
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

    # --- 1. Sorties brutes des Agents ---
    structured_json = Column(JSONB, nullable=True)      # Output Parsing Agent
    summary_output = Column(Text, nullable=True)          # Output Summary Agent
    diagram_output = Column(JSONB, nullable=True)         # Output Diagram Agent
    glossary_output = Column(JSONB, nullable=True)        # Output Glossary Agent
    written_doc = Column(Text, nullable=True)              # Output Documentation Writer
    layout_output = Column(Text, nullable=True)            # Output Design/Layout Agent

    # --- 2. Évaluations JSON des 6 Agents (Pop-up Frontend) ---
    parsing_eval = Column(JSONB, nullable=True)          # Eval Parsing Agent
    summary_eval = Column(JSONB, nullable=True)          # Eval Summary Agent
    glossary_eval = Column(JSONB, nullable=True)         # Eval Glossary Agent
    diagram_eval = Column(JSONB, nullable=True)          # Eval Diagram Agent
    writer_eval = Column(JSONB, nullable=True)           # Eval Documentation Writer Agent
    layout_eval = Column(JSONB, nullable=True)           # Eval Layout Agent

    # --- 3. KPI Global combiné ---
    global_kpi_score = Column(Float, nullable=True)

    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    artifact = relationship("Artifact", back_populates="pipeline_runs")
    doc_version = relationship("DocVersion", back_populates="pipeline_run", uselist=False)

    def __repr__(self) -> str:
        return f"<PipelineRun id={self.id} stage={self.current_stage} score={self.global_kpi_score}>"


# ============================================
# Ticket / TicketComment / TicketEvent
# ============================================

class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        UniqueConstraint("project_id", "source_path", name="uq_ticket_project_path"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    project_id = Column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    artifact_id = Column(
        UUID(as_uuid=True), ForeignKey("artifacts.id", ondelete="SET NULL"), nullable=True
    )
    source_path = Column(String(500), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(
        SAEnum(TicketStatus, name="ticket_status_enum"),
        nullable=False,
        default=TicketStatus.todo,
    )
    position = Column(Integer, nullable=False, default=0)
    checkbox_state = Column(String(20), nullable=True)
    file_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    project = relationship("Project")
    artifact = relationship("Artifact")
    comments = relationship(
        "TicketComment",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketComment.created_at",
    )
    events = relationship(
        "TicketEvent",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketEvent.created_at",
    )

    def __repr__(self) -> str:
        return f"<Ticket id={self.id} title={self.title!r} status={self.status}>"


class TicketComment(Base):
    __tablename__ = "ticket_comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    ticket_id = Column(
        UUID(as_uuid=True), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False
    )
    author_type = Column(
        SAEnum(AuthorType, name="author_type_enum"),
        nullable=False,
        default=AuthorType.human,
    )
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    ticket = relationship("Ticket", back_populates="comments")

    def __repr__(self) -> str:
        return f"<TicketComment id={self.id} ticket_id={self.ticket_id} author_type={self.author_type}>"


class TicketEvent(Base):
    __tablename__ = "ticket_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    ticket_id = Column(
        UUID(as_uuid=True), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False
    )
    event_type = Column(
        SAEnum(TicketEventType, name="ticket_event_type_enum"),
        nullable=False,
    )
    author_type = Column(
        SAEnum(AuthorType, name="author_type_enum"),
        nullable=False,
        default=AuthorType.agent,
    )
    payload = Column(JSONB, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    ticket = relationship("Ticket", back_populates="events")

    def __repr__(self) -> str:
        return f"<TicketEvent id={self.id} ticket_id={self.ticket_id} event_type={self.event_type}>"



