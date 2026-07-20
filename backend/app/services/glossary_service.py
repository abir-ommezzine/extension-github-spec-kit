import json
from typing import Dict, Any
# Importations des schémas requis
from app.schemas.glossary_agent_schema import GlossaryOutputModel
from app.schemas.parsing_agent_schema import ParsingAgentOutput
# Importations des composants et outils d'infrastructure
from app.utils.glossary_tools import GlossaryHarvesterService
from app.core.prompts import get_glossary_agent_prompt
from app.core.llm_client import ollama_openai_client, get_ollama_model
from app.core.llm_utils import parse_and_validate_json

class GlossaryAgentService:
    """
    Service d'orchestration pour le Glossary Agent.
    Exploite le client Ollama/OpenAI-compatible centralisé pour extraire, 
    classifier et définir les concepts métiers et techniques d'un projet.
    """

    def generate_glossary(
        self, 
        parsed_json_dict: Dict[str, Any], 
        glossary_spec_dict: Dict[str, Any]
    ) -> GlossaryOutputModel:
        """
        Exécute le pipeline complet d'extraction et d'ancrage sémantique du glossaire.
        """
        # 1. Validation structurelle de l'objet d'entrée (ParsingAgentOutput)
        # Assure l'intégrité fonctionnelle des données avant traitement
        ParsingAgentOutput(**parsed_json_dict)

        # 2. Outil 1 : Récolte déterministe des termes candidats (Contextual Term Harvester)
        # Analyse le texte pour extraire les acronymes, entités et normes implicites
        candidate_terms = GlossaryHarvesterService.harvest_candidates(parsed_json_dict)

        # 3. Construction du Prompt Système enrichi
        # Injection des spécifications de gouvernance et des jetons d'ancrage impératifs
        system_prompt = get_glossary_agent_prompt(glossary_spec_dict, candidate_terms)

        # 4. Payload d'entrée utilisateur
        # Transmission de l'intégralité du JSON épuré pour l'association des ancres textuelles
        user_prompt = json.dumps(parsed_json_dict, ensure_ascii=False)

        # 5. Inférence LLM via le client centralisé
        # Mode déterministe pur (temperature=0.0) et typage JSON strict imposé au modèle
        response = ollama_openai_client.chat.completions.create(
            model=get_ollama_model(),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.0
        )
        
        raw_output = response.choices[0].message.content

        # 6. Extraction Regex et validation mathématique finale via le schéma Pydantic
        return parse_and_validate_json(raw_output, GlossaryOutputModel)