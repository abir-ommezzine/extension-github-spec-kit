# app/core/llm_client.py
"""
llm_client.py — Gestionnaire centralise des connexions LLM (Ollama)
"""

import time
from openai import OpenAI, APIStatusError
from app.config import settings

# Client Ollama compatible OpenAI avec timeout augmente (5 minutes)
ollama_openai_client = OpenAI(
    base_url=f"{settings.OLLAMA_BASE_URL}/v1",
    api_key="ollama",
    timeout=300.0  # 5 minutes timeout (default is 60s)
)


def get_llm_model() -> str:
    """Retourne le nom du modele LLM configure dans le .env"""
    return settings.LLM_MODEL


def get_llm_client() -> OpenAI:
    """Retourne le client LLM configure (Ollama)."""
    return ollama_openai_client


def ollama_chat_with_retry(
    model: str,
    messages: list,
    response_format: dict = None,
    temperature: float = 0.0,
    max_tokens: int = 4096,
    max_retries: int = 3,
    base_delay: float = 1.0
):
    """
    Appel Ollama avec retry simple.
    """
    for attempt in range(max_retries):
        try:
            kwargs = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if response_format:
                kwargs["response_format"] = response_format
            
            return ollama_openai_client.chat.completions.create(**kwargs)
            
        except APIStatusError as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                print(f"   ⚠️ Ollama busy/error (tentative {attempt + 1}/{max_retries}). "
                      f"Attente {delay}s avant retry...")
                time.sleep(delay)
                continue
            else:
                raise
    
    raise APIStatusError("Max retries exceeded", response=None, body=None)