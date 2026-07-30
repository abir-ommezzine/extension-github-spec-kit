from pathlib import Path
from typing import Optional, List, Dict, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from pathlib import Path

from app.database import get_db
from app.models import (
    Project,
    Artifact,
    DocVersion,
    Ticket,
    TicketStatus,
    TicketEvent,
    TicketEventType,
    AuthorType,
)
from app.services.ticket_ingestion import (
    ingest_all_tasks,
    ingest_task_file,
    get_ticket_by_id,
    get_tickets_by_project,
    update_ticket_status,
    add_ticket_comment,
    add_agent_comment,
    get_ticket_events,
    get_ticket_comments,
    get_project_progress,
    apply_commit_refinement,
)
from app.utils.path_builder import BASE_DIR, extract_project_name_from_path

router = APIRouter()


class TicketResponse(BaseModel):
    id: str
    project_id: str
    artifact_id: Optional[str] = None
    source_path: str
    title: str
    description: Optional[str] = None
    status: str
    position: int
    checkbox_state: Optional[str] = None
    file_hash: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class TicketCommentResponse(BaseModel):
    id: str
    ticket_id: str
    author_type: str
    body: str
    created_at: str

    class Config:
        from_attributes = True


class TicketEventResponse(BaseModel):
    id: str
    ticket_id: str
    event_type: str
    author_type: str
    payload: Optional[Dict[str, Any]] = None
    created_at: str

    class Config:
        from_attributes = True


class StatusUpdateRequest(BaseModel):
    status: str = Field(..., description="New status: todo, in_progress, or done")


class CommentCreateRequest(BaseModel):
    body: str = Field(..., min_length=1, description="Comment body")
    author_type: Optional[str] = Field("human", description="human or agent")


class IngestRequest(BaseModel):
    tasks_dir: Optional[str] = None
    project_name: Optional[str] = None


class CommitRefineRequest(BaseModel):
    commit_message: str = Field(..., min_length=1)
    project_name: Optional[str] = None


class ProgressResponse(BaseModel):
    total: int
    done: int
    in_progress: int
    todo: int
    progress_pct: float


@router.get("/tickets", response_model=List[TicketResponse])
async def list_tickets(
    project_name: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    GET /tickets - List all tickets, optionally filtered by project or status.
    """
    if project_name:
        project = db.query(Project).filter(Project.name == project_name).first()
        if not project:
            return []
        tickets = get_tickets_by_project(db, str(project.id), status)
    else:
        query = db.query(Ticket)
        if status:
            try:
                status_enum = TicketStatus(status)
                query = query.filter(Ticket.status == status_enum)
            except ValueError:
                pass
        tickets = query.order_by(Ticket.project_id, Ticket.position).all()

    return [
        TicketResponse(
            id=str(t.id),
            project_id=str(t.project_id),
            artifact_id=str(t.artifact_id) if t.artifact_id else None,
            source_path=t.source_path,
            title=t.title,
            description=t.description,
            status=t.status.value,
            position=t.position,
            checkbox_state=t.checkbox_state,
            file_hash=t.file_hash,
            created_at=t.created_at.isoformat() if t.created_at else "",
            updated_at=t.updated_at.isoformat() if t.updated_at else "",
        )
        for t in tickets
    ]


@router.get("/tickets/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: str,
    db: Session = Depends(get_db),
):
    """
    GET /tickets/{id} - Get a single ticket by ID.
    """
    ticket = get_ticket_by_id(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return TicketResponse(
        id=str(ticket.id),
        project_id=str(ticket.project_id),
        artifact_id=str(ticket.artifact_id) if ticket.artifact_id else None,
        source_path=ticket.source_path,
        title=ticket.title,
        description=ticket.description,
        status=ticket.status.value,
        position=ticket.position,
        checkbox_state=ticket.checkbox_state,
        file_hash=ticket.file_hash,
        created_at=ticket.created_at.isoformat() if ticket.created_at else "",
        updated_at=ticket.updated_at.isoformat() if ticket.updated_at else "",
    )


@router.patch("/tickets/{ticket_id}/status", response_model=TicketResponse)
async def patch_ticket_status(
    ticket_id: str,
    request: StatusUpdateRequest,
    db: Session = Depends(get_db),
):
    """
    PATCH /tickets/{id}/status - Update ticket status.
    Backward moves (done -> in_progress, in_progress -> todo) are logged as status_override events.
    """
    try:
        target_status = TicketStatus(request.status)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {[s.value for s in TicketStatus]}",
        )

    ticket = update_ticket_status(db, ticket_id, request.status, AuthorType.human)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return TicketResponse(
        id=str(ticket.id),
        project_id=str(ticket.project_id),
        artifact_id=str(ticket.artifact_id) if ticket.artifact_id else None,
        source_path=ticket.source_path,
        title=ticket.title,
        description=ticket.description,
        status=ticket.status.value,
        position=ticket.position,
        checkbox_state=ticket.checkbox_state,
        file_hash=ticket.file_hash,
        created_at=ticket.created_at.isoformat() if ticket.created_at else "",
        updated_at=ticket.updated_at.isoformat() if ticket.updated_at else "",
    )


@router.post("/tickets/{ticket_id}/comments", response_model=TicketCommentResponse)
async def post_comment(
    ticket_id: str,
    request: CommentCreateRequest,
    db: Session = Depends(get_db),
):
    """
    POST /tickets/{id}/comments - Add a comment to a ticket.
    """
    try:
        author = AuthorType(request.author_type) if request.author_type else AuthorType.human
    except ValueError:
        author = AuthorType.human

    comment = add_ticket_comment(db, ticket_id, request.body, author)
    if not comment:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return TicketCommentResponse(
        id=str(comment.id),
        ticket_id=str(comment.ticket_id),
        author_type=comment.author_type.value,
        body=comment.body,
        created_at=comment.created_at.isoformat() if comment.created_at else "",
    )


@router.get("/tickets/{ticket_id}/comments", response_model=List[TicketCommentResponse])
async def list_comments(
    ticket_id: str,
    db: Session = Depends(get_db),
):
    """
    GET /tickets/{id}/comments - List all comments for a ticket.
    """
    ticket = get_ticket_by_id(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    comments = get_ticket_comments(db, ticket_id)
    return [
        TicketCommentResponse(
            id=str(c.id),
            ticket_id=str(c.ticket_id),
            author_type=c.author_type.value,
            body=c.body,
            created_at=c.created_at.isoformat() if c.created_at else "",
        )
        for c in comments
    ]


@router.get("/tickets/{ticket_id}/events", response_model=List[TicketEventResponse])
async def list_events(
    ticket_id: str,
    db: Session = Depends(get_db),
):
    """
    GET /tickets/{id}/events - List all events for a ticket.
    """
    ticket = get_ticket_by_id(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    events = get_ticket_events(db, ticket_id)
    return [
        TicketEventResponse(
            id=str(e.id),
            ticket_id=str(e.ticket_id),
            event_type=e.event_type.value,
            author_type=e.author_type.value,
            payload=e.payload,
            created_at=e.created_at.isoformat() if e.created_at else "",
        )
        for e in events
    ]


@router.post("/ingest", response_model=List[TicketResponse])
async def ingest_tasks(
    request: IngestRequest,
    db: Session = Depends(get_db),
):
    """
    POST /ingest - Ingest all tasks/*.md files into tickets (idempotent).
    """
    if request.tasks_dir:
        tasks_dir = Path(request.tasks_dir)
    else:
        tasks_dir = BASE_DIR / "specs" / "001-task-management-api"

    if not tasks_dir.exists():
        raise HTTPException(status_code=404, detail=f"Tasks directory not found: {tasks_dir}")

    project_name = request.project_name or extract_project_name_from_path(tasks_dir)

    tickets = ingest_all_tasks(db, tasks_dir, project_name)

    return [
        TicketResponse(
            id=str(t.id),
            project_id=str(t.project_id),
            artifact_id=str(t.artifact_id) if t.artifact_id else None,
            source_path=t.source_path,
            title=t.title,
            description=t.description,
            status=t.status.value,
            position=t.position,
            checkbox_state=t.checkbox_state,
            file_hash=t.file_hash,
            created_at=t.created_at.isoformat() if t.created_at else "",
            updated_at=t.updated_at.isoformat() if t.updated_at else "",
        )
        for t in tickets
    ]


@router.post("/commit-refine", response_model=List[TicketResponse])
async def commit_refine(
    request: CommitRefineRequest,
    db: Session = Depends(get_db),
):
    """
    POST /commit-refine - Refine ticket status based on commit message.
    Parses commit messages referencing task ids (e.g., T001) to sharpen In Progress/Done inference.
    """
    project_name = request.project_name or "001-task-management-api"
    project = db.query(Project).filter(Project.name == project_name).first()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project not found: {project_name}")

    tickets = apply_commit_refinement(db, request.commit_message, str(project.id))

    return [
        TicketResponse(
            id=str(t.id),
            project_id=str(t.project_id),
            artifact_id=str(t.artifact_id) if t.artifact_id else None,
            source_path=t.source_path,
            title=t.title,
            description=t.description,
            status=t.status.value,
            position=t.position,
            checkbox_state=t.checkbox_state,
            file_hash=t.file_hash,
            created_at=t.created_at.isoformat() if t.created_at else "",
            updated_at=t.updated_at.isoformat() if t.updated_at else "",
        )
        for t in tickets
    ]


@router.get("/progress", response_model=ProgressResponse)
async def project_progress(
    project_name: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    GET /progress - Get project-level progress (done/total tickets).
    """
    if project_name:
        project = db.query(Project).filter(Project.name == project_name).first()
        if not project:
            return ProgressResponse(total=0, done=0, in_progress=0, todo=0, progress_pct=0.0)
        progress = get_project_progress(db, str(project.id))
    else:
        tickets = db.query(Ticket).all()
        total = len(tickets)
        done = sum(1 for t in tickets if t.status == TicketStatus.done)
        in_progress = sum(1 for t in tickets if t.status == TicketStatus.in_progress)
        todo = sum(1 for t in tickets if t.status == TicketStatus.todo)
        progress = {
            "total": total,
            "done": done,
            "in_progress": in_progress,
            "todo": todo,
            "progress_pct": round(done / total * 100, 1) if total > 0 else 0.0,
        }

    return ProgressResponse(**progress)


@router.get("/tickets/{ticket_id}/doc-pdf")
async def get_ticket_doc_pdf(
    ticket_id: str,
    db: Session = Depends(get_db),
):
    """
    GET /tickets/{id}/doc-pdf - Get the latest doc_version PDF for the ticket's parent artifact.
    Returns clean empty state if the doc isn't generated yet.
    """
    from fastapi.responses import FileResponse
    from pathlib import Path as PathLib

    ticket = get_ticket_by_id(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if not ticket.artifact_id:
        return {"exists": False, "message": "No artifact linked to this ticket"}

    doc_version = (
        db.query(DocVersion)
        .filter(DocVersion.artifact_id == ticket.artifact_id)
        .order_by(DocVersion.version_no.desc())
        .first()
    )

    if not doc_version or not doc_version.pdf_path:
        return {"exists": False, "message": "Document not generated yet"}

    pdf_file = Path(doc_version.pdf_path)
    if not pdf_file.exists():
        return {"exists": False, "message": "PDF file not found on disk"}

    return FileResponse(
        path=str(pdf_file),
        media_type="application/pdf",
        filename=pdf_file.name,
        headers={"Content-Disposition": "inline"},
    )
