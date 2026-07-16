"""
database.py — Configuration de la connexion SQLAlchemy / PostgreSQL

Utilisé par le Documentation Agent (Feature 1) :
    context.md -> Parsing Agent -> Structured JSON
        -> Summary / Diagram / Glossary Agents
        -> Documentation Writer -> Design/Layout Agent
        -> Markdown/HTML -> PDF Generator

DATABASE_URL est lu depuis l'environnement (.env), jamais en dur.
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Charge le fichier .env situé à la racine de backend/
load_dotenv()

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:0000@localhost:5432/AgentDocx",
)

# pool_pre_ping évite les connexions mortes après une inactivité (utile en dev)
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency FastAPI : fournit une session DB et la ferme proprement."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()