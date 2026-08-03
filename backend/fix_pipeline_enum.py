from sqlalchemy import create_engine, text
from app.config import settings

engine = create_engine(settings.DATABASE_URL)
with engine.connect() as conn:
    conn.execute(text("ALTER TYPE pipeline_stage_enum ADD VALUE 'summary'"))
    conn.commit()
print('Added summary to pipeline_stage_enum')