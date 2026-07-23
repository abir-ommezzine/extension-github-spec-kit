# app/core/llm_client.py
"""
llm_client.py — Gestionnaire centralise des connexions LLM (Ollama Cloud)

Utilise la bibliotheque Python officielle 'ollama' pour communiquer
avec Ollama Cloud (gemma4:31b-cloud, etc.).

Configuration requise dans .env:
    OLLAMA_HOST=https://api.ollama.com
    OLLAMA_MODEL=gemma4:31b-cloud
    LLM_MODEL=gemma4:31b-cloud
    OLLAMA_API_KEY= votre_cle_api   (si necessaire)
"""

import os
import time
import ollama
from app.config import settings

OLLAMA_HOST = getattr(settings, 'OLLAMA_HOST', 'https://api.ollama.com')
OLLAMA_MODEL = getattr(settings, 'LLM_MODEL', 'gemma4:cloud')
OLLAMA_API_KEY = getattr(settings, 'OLLAMA_API_KEY', None)

os.environ['OLLAMA_HOST'] = OLLAMA_HOST

# Create client with auth headers if API key is provided
headers = {}
if OLLAMA_API_KEY:
    headers['Authorization'] = f'Bearer {OLLAMA_API_KEY}'

ollama_client = ollama.Client(host=OLLAMA_HOST, headers=headers)


def get_llm_model() -> str:
    """Retourne le nom du modele LLM configure dans le .env"""
    return OLLAMA_MODEL


def get_ollama_client():
    """Retourne le client Ollama configure."""
    return ollama_client


def ollama_chat(
    messages: list,
    temperature: float = 0.0,
    max_tokens: int = 8192,
    response_format: dict = None,
    max_retries: int = 3,
    base_delay: float = 2.0
):
    """
    Appel Ollama Cloud via la bibliotheque Python officielle.

    Args:
        messages: Liste de messages [{"role": "system"/"user", "content": "..."}]
        temperature: Temperature d'echantillonnage
        max_tokens: Nombre maximum de tokens en sortie
        response_format: {"type": "json_object"} pour forcer JSON
        max_retries: Nombre de tentatives en cas d'echec
        base_delay: Delai de base entre les retries

    Returns:
        Le contenu textuel de la reponse
    """
    # Construire les options
    options = {
        "temperature": temperature,
        "num_predict": max_tokens,
    }

    # Si format JSON demande, ajouter le flag
    format_type = None
    if response_format and response_format.get("type") == "json_object":
        format_type = "json"

    # Appel Ollama Cloud avec retry
    for attempt in range(max_retries):
        try:
            print(f"   ⏳ Appel Ollama Cloud (modele: {OLLAMA_MODEL}, tentative {attempt + 1}/{max_retries})...")

            response = ollama_client.chat(
                model=OLLAMA_MODEL,
                messages=messages,
                options=options,
                format=format_type
            )

            result = response.message.content
            print(f"   ✅ Reponse recue ({len(result)} chars)")

            return result

        except Exception as e:
            print(f"   ⚠️ Erreur Ollama Cloud: {e}")
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                print(f"   ⏳ Attente {delay}s avant retry...")
                time.sleep(delay)
            else:
                raise

    raise Exception("Max retries exceeded pour Ollama Cloud")