from sqlalchemy import create_engine, text
from app.config import settings

engine = create_engine(settings.DATABASE_URL)
with engine.connect() as conn:
    result = conn.execute(text("SELECT enumlabel FROM pg_enum WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'pipeline_stage_enum') ORDER BY enumsortorder"))
    for row in result:
        print(row[0])