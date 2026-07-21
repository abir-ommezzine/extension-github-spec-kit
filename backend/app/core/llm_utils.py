# # app/core/llm_utils.py
"""
llm_utils.py — Outils de nettoyage et d'extraction pour sécuriser les réponses d'Ollama.
"""

import re
import json
from typing import Type, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

def extract_json_from_text(text: str) -> str:
    """
    Isole et extrait la première structure JSON valide (délimitée par { et }) 
    présente dans une chaîne de caractères, en retirant le texte conversationnel 
    ou les balises de code Markdown.
    """
    if not text:
        return "{}"
        
    cleaned = text.strip()
    
    # 1. Suppression des blocs de code Markdown ```json ... ``` si présents
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
        
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
        
    cleaned = cleaned.strip()
    
    # 2. Si le texte commence et finit déjà par des accolades, c'est du JSON direct
    if cleaned.startswith("{") and cleaned.endswith("}"):
        return cleaned

    match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
    if match:
        return match.group(1)
        
    return cleaned


def parse_and_validate_json(raw_response: str, schema: Type[T]) -> T:
    """
    Extrait le JSON d'une réponse brute de LLM et le valide avec le schéma Pydantic fourni.
    """
    extracted_json = extract_json_from_text(raw_response)
    try:
        return schema.model_validate_json(extracted_json)
    except Exception as e:
        # En cas d'échec, nous journalisons le JSON extrait pour faciliter le débogage
        print(f"\n[❌ ERROR] Échec de la validation Pydantic.")
        print(f"JSON extrait tenté : \n{extracted_json}\n")
        raise e