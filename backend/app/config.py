# app/config.py
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

# __file__ est dans : racine/backend/app/config.py
# .parent             -> racine/backend/app/
# .parent.parent      -> racine/backend/
# .parent.parent.parent -> racine/ (Là où se trouve ton .env !)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"

class Settings(BaseSettings):
    # DATABASE_URL reste obligatoire pour démarrer l'application
    DATABASE_URL: str
    
    # Clé API OpenAI optionnelle pour ne pas bloquer les tests
    OPENAI_API_KEY: Optional[str] = None  
    
    PDF_STORAGE_DIR: str = "./storage/pdfs"
    LOG_LEVEL: str = "INFO"

    # Chargement dynamique du fichier .env depuis la racine globale
    model_config = SettingsConfigDict(
        env_file=ENV_PATH, 
        env_file_encoding="utf-8",
        extra="ignore"  # Ignore les autres variables du .env non définies ici
    )

settings = Settings()