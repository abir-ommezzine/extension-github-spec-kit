# app/core/metrics.py
"""
metrics.py — Calculateur de métriques d'évaluation pour la tâche de parsing.
Permet d'évaluer la fidélité, l'intégrité structurelle et le rappel d'extraction.
"""

import re
import difflib
from typing import List, Dict, Any
from app.schemas.parsing_agent_schema import ParsingAgentOutput
def calculate_sar(success: bool) -> float:
    """
    Schema Adherence Rate (SAR) :
    Retourne 100% si le JSON a pu être validé par Pydantic, sinon 0%.
    """
    return 100.0 if success else 0.0


def calculate_sir(input_sections: List[Dict[str, Any]], output_sections: List[Any]) -> float:
    """
    Structural Integrity Recall (SIR) :
    Mesure le pourcentage de sections physiques d'origine qui ont été 
    conservées dans le JSON final généré par le LLM.
    """
    if not input_sections:
        return 100.0
    return (len(output_sections) / len(input_sections)) * 100


def calculate_tfs(input_sections: List[Dict[str, Any]], output_sections: List[Any]) -> float:
    """
    Text Fidelity Score (TFS) :
    Compare textuellement le 'raw_content' d'origine et le 'raw_content' de sortie
    pour s'assurer que le LLM n'a pas résumé ou altéré les exigences.
    """
    input_map = {sec["title"].strip().lower(): sec["raw_content"].strip() for sec in input_sections}
    output_map = {sec.title.strip().lower(): sec.raw_content.strip() for sec in output_sections}
    
    if not input_map:
        return 100.0

    scores = []
    for title, in_content in input_map.items():
        if title in output_map:
            out_content = output_map[title]
            if in_content == out_content:
                scores.append(1.0)
            else:
                # Utilisation du ratio de similarité de Gestalt (SequenceMatcher)
                ratio = difflib.SequenceMatcher(None, in_content, out_content).ratio()
                scores.append(ratio)
        else:
            # Section perdue lors de la génération
            scores.append(0.0)
            
    return (sum(scores) / len(scores)) * 100 if scores else 0.0


def extract_heuristic_questions(raw_markdown: str) -> List[str]:
    """
    Extrait de manière déterministe les questions réelles présentes dans le texte source
    en cherchant les lignes contenant un point d'interrogation (?).
    Sert de 'Ground Truth' heuristique pour évaluer le rappel.
    """
    lines = raw_markdown.splitlines()
    questions = []
    for line in lines:
        line = line.strip()
        if "?" in line:
            # Nettoyage des listes Markdown, des préfixes 'Q:' ou 'Dialogue'
            cleaned = re.sub(r"^[-*\s]*([Qq]uestion|[Qq])?\s*[:\-\s]*", "", line)
            # Récupération de la phrase interrogative
            match = re.search(r"([^?]+\?)", cleaned)
            if match:
                questions.append(match.group(1).strip())
            else:
                questions.append(cleaned)
    return [q for q in questions if q]


def calculate_exr(raw_markdown: str, open_questions: List[str]) -> float:
    """
    Extraction Recall (ExR) :
    Mesure la capacité du LLM à trouver et extraire toutes les questions du document.
    """
    gt_questions = extract_heuristic_questions(raw_markdown)
    
    # AJUSTEMENT : Si le texte source ne contient aucun "?" explicite
    if not gt_questions:
        # Si le LLM trouve des questions pertinentes par déduction, c'est un bonus (100%)
        # Si le LLM n'en trouve pas, c'est correct aussi (100%)
        return 100.0
        
    found_count = 0
    for gt in gt_questions:
        for oq in open_questions:
            if gt.lower() in oq.lower() or oq.lower() in gt.lower():
                found_count += 1
                break
            elif difflib.SequenceMatcher(None, gt.lower(), oq.lower()).ratio() > 0.7:
                found_count += 1
                break
                
    return (found_count / len(gt_questions)) * 100