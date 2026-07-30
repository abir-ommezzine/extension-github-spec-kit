"""Add missing values to pipeline_stage_enum in PostgreSQL."""
import sys
sys.path.insert(0, r"C:\Users\MSI\Bureau\extension-github-spec-kit\backend")

from app.database import engine
from app.models import PipelineStage
from sqlalchemy import text

MISSING = ["summary", "glossary", "diagram", "writing", "layout", "rendering", "completed", "failed"]

with engine.connect() as conn:
    # Check what's already in the enum
    result = conn.execute(
        text("SELECT enum_range(NULL::pipeline_stage_enum)")
    )
    existing = result.scalar()
    print(f"Existing enum values: {existing}")

    for val in MISSING:
        if val not in (existing or ""):
            try:
                conn.execute(text(f"ALTER TYPE pipeline_stage_enum ADD VALUE '{val}'"))
                print(f"  Added: {val}")
            except Exception as e:
                print(f"  Skipped {val}: {e}")

    conn.commit()

print("Done.")
