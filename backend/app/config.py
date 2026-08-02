# app/config.py
import os
from pathlib import Path
from typing import Optional, Literal
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"

class Settings(BaseSettings):
    DATABASE_URL: str
    OPENAI_API_KEY: Optional[str] = None  
    
    # --- LLM PROVIDER CONFIGURATION ---
    # Supported providers: "ollama", "openai", "anthropic", "groq", "openai_compatible", "huggingface", "nvidia"
    LLM_PROVIDER: Literal["ollama", "openai", "anthropic", "groq", "openai_compatible", "huggingface", "nvidia"] = "ollama"
    
    # Ollama settings
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "gemma4:31b-cloud"
    OLLAMA_API_KEY: Optional[str] = None
    
    # OpenAI settings
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_BASE_URL: Optional[str] = None
    
    # Anthropic settings
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"
    
    # Groq settings (OpenAI-compatible)
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    
    # NVIDIA NIM settings (OpenAI-compatible)
    NVIDIA_API_KEY: Optional[str] = None
    NVIDIA_MODEL: str = "nvidia/nemotron-3-ultra"
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    
    # Hugging Face settings (OpenAI-compatible inference API)
    HUGGINGFACE_API_KEY: Optional[str] = None
    HUGGINGFACE_MODEL: str = "meta-llama/Llama-3.3-70B-Instruct"
    HUGGINGFACE_BASE_URL: str = "https://api-inference.huggingface.co/v1"
    
    # Generic OpenAI-compatible API settings
    OPENAI_COMPATIBLE_API_KEY: Optional[str] = None
    OPENAI_COMPATIBLE_MODEL: str = "gpt-4o"
    OPENAI_COMPATIBLE_BASE_URL: Optional[str] = None
    
    PDF_STORAGE_DIR: str = "./storage/pdfs"
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=ENV_PATH, 
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()