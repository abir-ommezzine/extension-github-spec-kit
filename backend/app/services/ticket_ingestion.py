import hashlib
import re
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.models import (
    Project,
    Artifact,
    Ticket,
    TicketStatus,
    TicketEvent,
    TicketEventType,
    AuthorType,
)
from app.utils.path_builder import extract_project_name_from_path


def compute_file_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def parse_task_lines(content: str) -> List[Dict[str, Any]]:
    """
    Parse a tasks/*.md file and extract individual task items.
    Returns a list of dicts with: id, title, description, checkbox_state, raw_line
    """
    lines = content.splitlines()
    tasks = []
    
    current_task = None
    in_task_list = False
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Detect task list items: - [x] T001 Description or - [ ] T001 Description
        task_match = re.match(r'^-\s*\[([xX\s])\]\s*(.+)$', stripped)
        if task_match:
            checkbox = task_match.group(1)
            task_text = task_match.group(2).strip()
            
            # Extract task ID (e.g., T001, T002)
            id_match = re.match(r'^(T\d+)', task_text)
            task_id = id_match.group(1) if id_match else f"task_{len(tasks) + 1}"
            
            # Determine checkbox state
            if checkbox.lower() == 'x':
                checkbox_state = "checked"
            else:
                checkbox_state = "unchecked"
            
            # Extract title (first part after ID)
            title = task_text
            if id_match:
                title = task_text[len(task_id):].strip()
                # Remove leading punctuation like ":" or "-"
                title = title.lstrip(":- ").strip()
            
            tasks.append({
                "id": task_id,
                "title": title or task_text,
                "description": "",
                "checkbox_state": checkbox_state,
                "raw_line": stripped,
                "line_number": i,
            })
            in_task_list = True
            continue
        
        # If we're in a task list and hit a non-task line, check if it's a continuation
        if in_task_list and stripped and not stripped.startswith("- ["):
            # This could be a description for the last task
            if tasks and not stripped.startswith("#"):
                tasks[-1]["description"] += ("\n" if tasks[-1]["description"] else "") + stripped
        elif stripped.startswith("#"):
            # New section, reset
            in_task_list = False
    
    return tasks


def infer_status_from_checkbox(checkbox_state: str) -> TicketStatus:
    """
    Infer ticket status from checkbox state:
    - unchecked -> todo
    - checked -> done
    """
    if checkbox_state == "checked":
        return TicketStatus.done
    return TicketStatus.todo


def can_auto_transition(current: TicketStatus, target: TicketStatus) -> bool:
    """
    Auto-moves only go forward: todo -> in_progress -> done.
    Backward moves require human override.
    """
    order = {
        TicketStatus.todo: 0,
        TicketStatus.in_progress: 1,
        TicketStatus.done: 2,
    }
    return order.get(target, 0) >= order.get(current, 0)


def ingest_task_file(
    db: Session,
    file_path: Path,
    project: Project,
    artifact: Optional[Artifact] = None,
) -> List[Ticket]:
    """
    Ingest a single task file into the tickets table.
    Idempotent: if tickets already exist (same project + source_path + task_id), update in place.
    Returns list of created/updated tickets.
    """
    file_path_str = str(file_path.resolve())
    content = file_path.read_text(encoding="utf-8")
    file_hash = compute_file_hash(content)
    
    # Parse individual tasks from the file
    parsed_tasks = parse_task_lines(content)
    
    tickets = []
    
    for parsed in parsed_tasks:
        # Create a unique source path per task (file + task ID)
        task_source_path = f"{file_path_str}#{parsed['id']}"
        
        existing_ticket = (
            db.query(Ticket)
            .filter(
                Ticket.project_id == project.id,
                Ticket.source_path == task_source_path,
            )
            .first()
        )
        
        inferred_status = infer_status_from_checkbox(parsed["checkbox_state"])
        
        if existing_ticket:
            updated = False
            
            if existing_ticket.title != parsed["title"]:
                existing_ticket.title = parsed["title"]
                updated = True
            
            if existing_ticket.description != parsed["description"]:
                existing_ticket.description = parsed["description"]
                updated = True
            
            if existing_ticket.checkbox_state != parsed["checkbox_state"]:
                existing_ticket.checkbox_state = parsed["checkbox_state"]
                updated = True
            
            if existing_ticket.file_hash != file_hash:
                existing_ticket.file_hash = file_hash
                updated = True
            
            if existing_ticket.artifact_id != (artifact.id if artifact else None):
                existing_ticket.artifact_id = artifact.id if artifact else None
                updated = True
            
            if updated:
                old_status = existing_ticket.status
                
                if can_auto_transition(old_status, inferred_status):
                    if old_status != inferred_status:
                        existing_ticket.status = inferred_status
                        db.add(TicketEvent(
                            ticket_id=existing_ticket.id,
                            event_type=TicketEventType.status_change,
                            author_type=AuthorType.agent,
                            payload={
                                "from": old_status.value,
                                "to": inferred_status.value,
                                "source": "checkbox_inference",
                            },
                        ))
                else:
                    if old_status != inferred_status:
                        db.add(TicketEvent(
                            ticket_id=existing_ticket.id,
                            event_type=TicketEventType.status_override,
                            author_type=AuthorType.agent,
                            payload={
                                "from": old_status.value,
                                "to": inferred_status.value,
                                "source": "checkbox_inference_blocked",
                                "message": "Backward move blocked by auto-inference. Requires human override.",
                            },
                        ))
            
            db.add(existing_ticket)
            db.commit()
            db.refresh(existing_ticket)
            tickets.append(existing_ticket)
        else:
            ticket = Ticket(
                project_id=project.id,
                artifact_id=artifact.id if artifact else None,
                source_path=task_source_path,
                title=parsed["title"],
                description=parsed["description"],
                status=inferred_status,
                position=0,
                checkbox_state=parsed["checkbox_state"],
                file_hash=file_hash,
            )
            
            db.add(ticket)
            db.commit()
            db.refresh(ticket)
            
            db.add(TicketEvent(
                ticket_id=ticket.id,
                event_type=TicketEventType.status_change,
                author_type=AuthorType.agent,
                payload={
                    "from": None,
                    "to": inferred_status.value,
                    "source": "initial_ingestion",
                },
            ))
            db.commit()
            
            tickets.append(ticket)
    
    return tickets


def ingest_all_tasks(
    db: Session,
    tasks_dir: Path,
    project_name: Optional[str] = None,
) -> List[Ticket]:
    """
    Scan a tasks/ directory and ingest all .md files.
    Idempotent: re-running updates existing tickets in place.
    """
    if not tasks_dir.exists():
        return []
    
    if not project_name:
        project_name = extract_project_name_from_path(tasks_dir)
    
    project = db.query(Project).filter(Project.name == project_name).first()
    if not project:
        project = Project(name=project_name)
        db.add(project)
        db.commit()
        db.refresh(project)
    
    all_tickets = []
    task_files = sorted(tasks_dir.glob("*.md"))
    
    for task_file in task_files:
        artifact = (
            db.query(Artifact)
            .filter(
                Artifact.project_id == project.id,
                Artifact.source_path == str(task_file.resolve()),
            )
            .first()
        )
        
        tickets = ingest_task_file(db, task_file, project, artifact)
        all_tickets.extend(tickets)
    
    return all_tickets


def get_ticket_by_id(db: Session, ticket_id: str) -> Optional[Ticket]:
    return db.query(Ticket).filter(Ticket.id == ticket_id).first()


def get_tickets_by_project(
    db: Session,
    project_id: str,
    status_filter: Optional[str] = None,
) -> List[Ticket]:
    query = db.query(Ticket).filter(Ticket.project_id == project_id)
    if status_filter:
        try:
            status_enum = TicketStatus(status_filter)
            query = query.filter(Ticket.status == status_enum)
        except ValueError:
            pass
    return query.order_by(Ticket.position).all()


def update_ticket_status(
    db: Session,
    ticket_id: str,
    new_status: str,
    author_type: AuthorType = AuthorType.human,
) -> Optional[Ticket]:
    """
    Update ticket status. If the move is backward (auto-inference would block it),
    log it as a status_override event.
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        return None
    
    try:
        target_status = TicketStatus(new_status)
    except ValueError:
        return None
    
    old_status = ticket.status
    
    if old_status == target_status:
        return ticket
    
    if can_auto_transition(old_status, target_status):
        ticket.status = target_status
        db.add(TicketEvent(
            ticket_id=ticket.id,
            event_type=TicketEventType.status_change,
            author_type=author_type,
            payload={
                "from": old_status.value,
                "to": target_status.value,
                "source": "api_patch",
            },
        ))
    else:
        ticket.status = target_status
        db.add(TicketEvent(
            ticket_id=ticket.id,
            event_type=TicketEventType.status_override,
            author_type=author_type,
            payload={
                "from": old_status.value,
                "to": target_status.value,
                "source": "api_patch",
            },
        ))
    
    db.commit()
    db.refresh(ticket)
    return ticket


def add_ticket_comment(
    db: Session,
    ticket_id: str,
    body: str,
    author_type: AuthorType = AuthorType.human,
) -> Optional[Ticket]:
    from app.models import TicketComment
    
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        return None
    
    comment = TicketComment(
        ticket_id=ticket.id,
        author_type=author_type,
        body=body,
    )
    db.add(comment)
    
    db.add(TicketEvent(
        ticket_id=ticket.id,
        event_type=TicketEventType.comment_added,
        author_type=author_type,
        payload={"comment_id": str(comment.id)},
    ))
    
    db.commit()
    db.refresh(comment)
    return comment


def get_ticket_events(
    db: Session,
    ticket_id: str,
) -> List[TicketEvent]:
    return (
        db.query(TicketEvent)
        .filter(TicketEvent.ticket_id == ticket_id)
        .order_by(TicketEvent.created_at)
        .all()
    )


def get_ticket_comments(
    db: Session,
    ticket_id: str,
) -> List:
    from app.models import TicketComment
    return (
        db.query(TicketComment)
        .filter(TicketComment.ticket_id == ticket_id)
        .order_by(TicketComment.created_at)
        .all()
    )


def add_agent_comment(
    db: Session,
    ticket_id: str,
    body: str,
):
    return add_ticket_comment(db, ticket_id, body, AuthorType.agent)


def get_project_progress(
    db: Session,
    project_id: str,
) -> Dict[str, Any]:
    tickets = db.query(Ticket).filter(Ticket.project_id == project_id).all()
    total = len(tickets)
    done = sum(1 for t in tickets if t.status == TicketStatus.done)
    in_progress = sum(1 for t in tickets if t.status == TicketStatus.in_progress)
    todo = sum(1 for t in tickets if t.status == TicketStatus.todo)
    
    return {
        "total": total,
        "done": done,
        "in_progress": in_progress,
        "todo": todo,
        "progress_pct": round(done / total * 100, 1) if total > 0 else 0.0,
    }


def find_tickets_by_commit_message(
    db: Session,
    commit_message: str,
    project_id: str,
) -> List[Ticket]:
    """
    Parse commit messages referencing a task id to sharpen status inference.
    Looks for patterns like: T001, T002, etc. or ticket IDs.
    """
    ticket_ids = re.findall(r'\bT(\d+)\b', commit_message, re.IGNORECASE)
    tickets = []
    for tid in ticket_ids:
        ticket = db.query(Ticket).filter(
            Ticket.project_id == project_id,
            Ticket.title.contains(f"T{tid}"),
        ).first()
        if ticket:
            tickets.append(ticket)
    return tickets


def apply_commit_refinement(
    db: Session,
    commit_message: str,
    project_id: str,
) -> List[Ticket]:
    """
    Refine In Progress/Done inference based on commit messages.
    If commit mentions 'finish', 'complete', or 'done' -> move to done.
    If commit mentions 'start', 'begin', or 'implement' -> move to in_progress.
    """
    tickets = find_tickets_by_commit_message(db, commit_message, project_id)
    msg_lower = commit_message.lower()
    
    for ticket in tickets:
        if any(word in msg_lower for word in ["finish", "complete", "done", "close"]):
            update_ticket_status(db, str(ticket.id), "done", AuthorType.agent)
        elif any(word in msg_lower for word in ["start", "begin", "implement", "wip"]):
            update_ticket_status(db, str(ticket.id), "in_progress", AuthorType.agent)
    
    return tickets