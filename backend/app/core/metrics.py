# app/core/metrics.py
"""
metrics.py — Calculateur de métriques d'évaluation pour la tâche de parsing (Version Fusionnée).
Évalue la fidélité, l'intégrité structurelle, le rappel d'extraction et la topologie du graphe.
"""

import re
import difflib
from typing import List, Dict, Any

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
    if not output_sections:
        return 0.0
    return (len(output_sections) / len(input_sections)) * 100


def calculate_tfs(input_sections: List[Dict[str, Any]], output_sections: List[Any]) -> float:
    """
    Text Fidelity Score (TFS) Amélioré :
    Compare le contenu textuel brut pour s'assurer qu'aucune information n'a été 
    altérée ou résumée. Plus robuste face aux déplacements ou changements de casse des titres.
    """
    if not input_sections:
        return 100.0
        
    input_map = {sec["title"].strip().lower(): sec["raw_content"].strip() for sec in input_sections}
    output_map = {getattr(sec, "title", sec.get("title", "")).strip().lower(): getattr(sec, "raw_content", sec.get("raw_content", "")).strip() for sec in output_sections}

    scores = []
    for title, in_content in input_map.items():
        if not in_content: # Ignore les sections vides qui servent uniquement de conteneurs structurels
            continue
            
        if title in output_map:
            out_content = output_map[title]
            if in_content == out_content:
                scores.append(1.0)
            else:
                ratio = difflib.SequenceMatcher(None, in_content, out_content).ratio()
                scores.append(ratio)
        else:
            # Recherche textuelle globale fallback au cas où le titre a légèrement bougé
            matched_fallback = False
            for out_title, out_content in output_map.items():
                if in_content in out_content or out_content in in_content:
                    scores.append(difflib.SequenceMatcher(None, in_content, out_content).ratio())
                    matched_fallback = True
                    break
            if not matched_fallback:
                scores.append(0.0)
            
    return (sum(scores) / len(scores)) * 100 if scores else 100.0


def extract_heuristic_questions(raw_markdown: str) -> List[str]:
    """
    Extrait de manière déterministe les questions réelles présentes dans le texte source
    en cherchant les lignes contenant un point d'interrogation (?).
    """
    lines = raw_markdown.splitlines()
    questions = []
    for line in lines:
        line = line.strip()
        if "?" in line:
            cleaned = re.sub(r"^[-*\s]*([Qq]uestion|[Qq])?\s*[:\-\s]*", "", line)
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
    
    if not gt_questions:
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


def calculate_gri(elements: List[Any], relationships: List[Any]) -> float:
    """
    Graph Relational Integrity (GRI) - NOUVELLE MÉTRIQUE FUSIONNÉE :
    S'assure de la cohérence interne du graphe extrait. Valide que les liens 
    pointent vers des nœuds existants dans la liste des éléments.
    """
    if not relationships:
        return 100.0 # Pas de relation extraite, cohérence nominale valide
        
    # Collecte de tous les identifiants valides et des extraits de contenus courts
    valid_nodes = set()
    for el in elements:
        ident = getattr(el, "identifier", el.get("identifier"))
        content = getattr(el, "content", el.get("content", ""))
        if ident:
            valid_nodes.add(str(ident).lower())
        if content:
            valid_nodes.add(content[:30].strip().lower()) # Ancre de contenu court

    valid_relations = 0
    for rel in relationships:
        source = str(getattr(rel, "from", rel.get("from", ""))).lower()
        target = str(getattr(rel, "to", rel.get("to", ""))).lower()
        
        # Vérification si la source et la cible se rattachent à des entités réelles
        source_valid = any(source in node or node in source for node in valid_nodes)
        target_valid = any(target in node or node in target for node in valid_nodes)
        
        if source_valid and target_valid:
            valid_relations += 1
            
    return (valid_relations / len(relationships)) * 100