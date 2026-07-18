import os
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.agents.parsing_agent import parse_context_md
from app.models import PipelineRun, PipelineStage, Artifact


async def run_parsing_stage(db: Session, artifact: Artifact, file_path: str = None) -> PipelineRun:
    """
    Run the Parsing Agent on an artifact's markdown file.
    Creates a PipelineRun, executes parsing, saves structured JSON.
    
    Args:
        db: Database session
        artifact: The artifact to parse
        file_path: Optional actual file path (if different from artifact.source_path)
    """
    # 1. Create PipelineRun record
    pipeline_run = PipelineRun(
        artifact_id=artifact.id,
        current_stage=PipelineStage.parsing,
    )
    db.add(pipeline_run)
    db.commit()
    db.refresh(pipeline_run)

    try:
        # 2. Determine file path
        read_path = file_path or artifact.source_path
        
        # Handle relative paths from project root
        if not os.path.isabs(read_path):
            backend_dir = Path(__file__).resolve().parent.parent.parent
            project_root = backend_dir.parent
            possible_paths = [
                Path(read_path),
                project_root / read_path,
                backend_dir / read_path,
            ]
            for p in possible_paths:
                p = Path(str(p).replace('/', os.sep))
                if p.exists():
                    read_path = str(p.resolve())
                    break

        # 3. Read the markdown file
        if not os.path.exists(read_path):
            raise FileNotFoundError(f"File not found: {read_path}")

        with open(read_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 4. Run Parsing Agent
        structured = await parse_context_md(content, artifact.source_path)

        # 5. Save success
        pipeline_run.structured_json = structured
        pipeline_run.current_stage = PipelineStage.completed
        pipeline_run.completed_at = datetime.utcnow()
        db.commit()

        return pipeline_run

    except Exception as e:
        # 6. Save failure
        pipeline_run.current_stage = PipelineStage.failed
        pipeline_run.error_message = str(e)
        db.commit()
        raise