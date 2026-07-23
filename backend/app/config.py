# app/config.py
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

# Look for .env in backend/ folder
BASE_DIR = Path(__file__).resolve().parent.parent  # -> backend/
ENV_PATH = BASE_DIR / ".env"

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://speckit:speckit@localhost:5432/speckit"
    
    # OpenAI (legacy)
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"
    
    # Generic LLM settings
    LLM_BASE_URL: Optional[str] = None
    LLM_API_KEY: Optional[str] = None
    LLM_MODEL: str = "gpt-4o"
    
    # Ollama settings
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_HOST: str = "https://api.ollama.com"
    OLLAMA_API_KEY: Optional[str] = None
    OLLAMA_MODEL: str = "llama3.1:8b"
    
    # Storage & Logging
    PDF_STORAGE_DIR: str = "./storage/pdfs"
    LOG_LEVEL: str = "INFO"
    
    # Pydantic v2 config (ONLY this, no class Config)
    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()