from sqlalchemy import create_engine, text
from app.config import settings

engine = create_engine(settings.DATABASE_URL)
with engine.connect() as conn:
    conn.execute(text("ALTER TYPE artifact_type_enum ADD VALUE 'requirements'"))
    conn.commit()
print('Added requirements to enum')