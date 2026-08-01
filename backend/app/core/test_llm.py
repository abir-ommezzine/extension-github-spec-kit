# app/core/test_llm.py
"""
test_llm.py — Script de diagnostic robuste pour tous les providers LLM.
"""

import sys
from pydantic import BaseModel, Field
from app.core.llm_client import chat_completion, chat_completion_structured, get_default_model
from app.core.llm_utils import parse_and_validate_json

# Schéma de test
class DiagnosticResponse(BaseModel):
    connection_status: str = Field(..., description="Doit être 'SUCCESS' ou 'FAILURE'")
    model_name_confirmed: str = Field(..., description="Le nom exact du modèle qui a répondu")
    greeting_message: str = Field(..., description="Un message de bienvenue amical")

def run_diagnostics():
    model = get_default_model()
    print("=" * 60)
    print("   DIAGNOSTIC DU CLIENT LLM (PROVIDER-AGNOSTIC) - SECURISE")
    print("=" * 60)
    print(f"[CFG] Modele configure : {model}")
    print(f"[CONN] Connexion en cours...\n")

    # --- TEST 1 : Completion standard ---
    print("--- TEST 1 : Completion de texte standard ---")
    try:
        response = chat_completion(
            model=model,
            messages=[
                {"role": "system", "content": "Tu es un assistant de test. Reponds de maniere tres concise."},
                {"role": "user", "content": "Dis-moi bonjour et confirme que tu fonctionnes correctement."}
            ],
            max_tokens=50,
            temperature=0.3
        )
        answer = response.choices[0].message.content.strip()
        print(f"[OK] Reponse recue avec succes !")
        print(f"Bot : \"{answer}\"")
    except Exception as e:
        print(f"[ERREUR] ECHEC DU TEST 1 : Impossible de communiquer avec le provider.")
        print(f"    Erreur : {e}")
        sys.exit(1)

    print("-" * 60)

    # --- TEST 2 : JSON Mode avec Extracteur Robuste ---
    print("--- TEST 2 : Validation du Mode JSON (Pydantic + Regex) ---")
    print("[WAIT] Envoi d'une requete structuree...")
    
    schema_instruction = (
        "Tu es un systeme automatise de diagnostic technique.\n"
        "Tu dois obligatoirement repondre sous la forme d'un objet JSON unique respectant cette structure :\n"
        "{\n"
        '  "connection_status": "SUCCESS",\n'
        '  "model_name_confirmed": "nom-du-modele",\n'
        '  "greeting_message": "ton message de bienvenue"\n'
        "}\n\n"
        "CONSIGNE STRICTE : Ne genere aucun texte d'introduction ou de conclusion en dehors du JSON. "
        "Pas de balise markdown, pas de phrases explicatives."
    )

    try:
        # Test avec l'interface structuree unifiee
        parsed_data = chat_completion_structured(
            model=model,
            messages=[
                {"role": "system", "content": schema_instruction},
                {"role": "user", "content": f"Genere un diagnostic de succes pour le modele '{model}'."}
            ],
            response_format=DiagnosticResponse,
            temperature=0.0
        )
        
        print(f"[OK] Extraction et validation JSON reussies avec succes !")
        print(f"Donnees structurees obtenues :")
        print(f"    - Statut de connexion : {parsed_data.connection_status}")
        print(f"    - Modele confirme     : {parsed_data.model_name_confirmed}")
        print(f"    - Message de l'IA     : {parsed_data.greeting_message}")
        
        print("\n" + "=" * 60)
        print("[SUCCESS] Votre configuration LLM est 100% operationnelle !")
        print("   Le provider et la validation de schema Pydantic fonctionnent parfaitement.")
        print("=" * 60)

    except Exception as e:
        print(f"[ERREUR] ECHEC DU TEST 2 : Le modele n'a pas pu etre parse.")
        print(f"    Detail de l'erreur : {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_diagnostics()