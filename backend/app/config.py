# app/config.py
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

# Détermine le répertoire de base du projet
# Si WORKSPACE_DIR est défini (par l'extension), l'utiliser, sinon calculer depuis __file__
if os.environ.get("WORKSPACE_DIR"):
    BASE_DIR = Path(os.environ["WORKSPACE_DIR"])
else:
    BASE_DIR = Path(__file__).resolve().parent.parent.parent

ENV_PATH = BASE_DIR / ".env"

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://speckit:speckit@localhost:5432/speckit"  # Valeur par défaut
    OPENAI_API_KEY: Optional[str] = None  
    
    # --- AJOUT CONFIGURATION OLLAMA ---
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "gemma4:31b-cloud"
    
    PDF_STORAGE_DIR: str = "./storage/pdfs"
    LOG_LEVEL: str = "INFO"
    
    # --- TARGET PROJECT CONFIGURATION ---
    # Path to the project being worked on (where current-task.json should be watched)
    TARGET_PROJECT_PATH: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH),  # Convertir en string pour compatibilité
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False  # Ignorer la casse des variables d'environnement
    )

settings = Settings()