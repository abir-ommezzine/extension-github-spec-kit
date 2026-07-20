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


# ===========================================================================
# MÉTRIQUES ADDITIONNELLES POUR LE SUMMARY AGENT
# ===========================================================================

def calculate_wca(executive_brief: str, min_words: int = 30, max_words: int = 150) -> float:
    """
    Word Count Adherence (WCA) :
    Vérifie le respect des contraintes strictes de longueur pour le résumé exécutif.
    Retourne 100% si la longueur est respectée, sinon applique une pénalité linéaire.
    """
    if not executive_brief:
        return 0.0
    
    words = executive_brief.split()
    word_count = len(words)
    
    if min_words <= word_count <= max_words:
        return 100.0
        
    if word_count < min_words:
        deviation = (min_words - word_count) / min_words
    else:
        deviation = (word_count - max_words) / max_words
        
    return max(0.0, (1.0 - deviation) * 100)


def calculate_gsc(languages_and_frameworks: List[str], parsed_elements: List[Dict[str, Any]]) -> float:
    """
    Graph Stack Content (GSC) :
    Mesure le taux d'alignement de la pile technique résumée par rapport aux éléments 
    formellement identifiés par le Parsing Agent (type 'tool_configuration' ou attributs).
    """
    if not languages_and_frameworks:
        return 100.0
    if not parsed_elements:
        return 0.0

    valid_references = set()
    for el in parsed_elements:
        content = el.get("content", "").lower()
        ident = el.get("identifier", "").lower()
        valid_references.add(content)
        valid_references.add(ident)
        
        attributes = el.get("attributes", {})
        if isinstance(attributes, dict):
            for val in attributes.values():
                valid_references.add(str(val).lower())

    matched_count = 0
    for tech in languages_and_frameworks:
        tech_lower = tech.lower()
        if any(tech_lower in ref or ref in tech_lower for ref in valid_references):
            matched_count += 1

    return (matched_count / len(languages_and_frameworks)) * 100


def calculate_mac(maturity_assessment: str, structural_gaps: List[Dict[str, Any]]) -> float:
    """
    Maturity Assessment Coherence (MAC) :
    Évalue si la synthèse narrative prend correctement en compte les lacunes documentaires.
    Vérifie l'analyse critique par rapport aux anomalies structurelles présentes.
    """
    if not structural_gaps:
        return 100.0
    if not maturity_assessment:
        return 0.0

    assessment_lower = maturity_assessment.lower()
    matched_gaps = 0

    for gap in structural_gaps:
        missing_sec = gap.get("missing_section", "").lower()
        if missing_sec in assessment_lower or any(k in assessment_lower for k in ["gap", "miss", "manqu"]):
            matched_gaps += 1

    return (matched_gaps / len(structural_gaps)) * 100


# ===========================================================================
# MÉTRIQUES ADDITIONNELLES POUR LE GLOSSARY AGENT
# ===========================================================================

def calculate_ata(items: List[Dict[str, Any]]) -> float:
    """
    Anti-Tautology Adherence (ATA) :
    Évalue le respect strict de la règle anti-tautologie. Calcule le pourcentage 
    de termes dont la définition opérationnelle ne contient pas le terme lui-même 
    (insensible à la casse).
    """
    if not items:
        return 100.0
        
    violations = 0
    for item in items:
        term = str(item.get("term", "")).strip().lower()
        definition = str(item.get("project_definition", "")).strip().lower()
        
        if term and term in definition:
            violations += 1
            
    return ((len(items) - violations) / len(items)) * 100


def calculate_cap(items: List[Dict[str, Any]], parsed_elements: List[Dict[str, Any]], parsed_sections: List[Dict[str, Any]]) -> float:
    """
    Contextual Anchor Precision (CAP) :
    Mesure la précision géométrique de l'ancrage contextuel. Vérifie le pourcentage 
    d'éléments du glossaire dont le champ 'contextual_anchor' correspond exactement 
    à un identifiant de nœud micro ('identifier') ou à un titre de section macro valide.
    """
    if not items:
        return 100.0

    valid_anchors = set()
    for el in parsed_elements:
        ident = el.get("identifier")
        if ident:
            valid_anchors.add(str(ident).strip().lower())
            
    for sec in parsed_sections:
        title = sec.get("title")
        if title:
            valid_anchors.add(str(title).strip().lower())

    matched_anchors = 0
    for item in items:
        anchor = str(item.get("contextual_anchor", "")).strip().lower()
        if anchor in valid_anchors:
            matched_anchors += 1

    return (matched_anchors / len(items)) * 100
# # app/core/metrics.py
# """
# metrics.py — Calculateur de métriques d'évaluation pour la tâche de parsing (Version Fusionnée).
# Évalue la fidélité, l'intégrité structurelle, le rappel d'extraction et la topologie du graphe.
# """

# import re
# import difflib
# from typing import List, Dict, Any

# def calculate_sar(success: bool) -> float:
#     """
#     Schema Adherence Rate (SAR) :
#     Retourne 100% si le JSON a pu être validé par Pydantic, sinon 0%.
#     """
#     return 100.0 if success else 0.0


# def calculate_sir(input_sections: List[Dict[str, Any]], output_sections: List[Any]) -> float:
#     """
#     Structural Integrity Recall (SIR) :
#     Mesure le pourcentage de sections physiques d'origine qui ont été 
#     conservées dans le JSON final généré par le LLM.
#     """
#     if not input_sections:
#         return 100.0
#     if not output_sections:
#         return 0.0
#     return (len(output_sections) / len(input_sections)) * 100


# def calculate_tfs(input_sections: List[Dict[str, Any]], output_sections: List[Any]) -> float:
#     """
#     Text Fidelity Score (TFS) Amélioré :
#     Compare le contenu textuel brut pour s'assurer qu'aucune information n'a été 
#     altérée ou résumée. Plus robuste face aux déplacements ou changements de casse des titres.
#     """
#     if not input_sections:
#         return 100.0
        
#     input_map = {sec["title"].strip().lower(): sec["raw_content"].strip() for sec in input_sections}
#     output_map = {getattr(sec, "title", sec.get("title", "")).strip().lower(): getattr(sec, "raw_content", sec.get("raw_content", "")).strip() for sec in output_sections}

#     scores = []
#     for title, in_content in input_map.items():
#         if not in_content: # Ignore les sections vides qui servent uniquement de conteneurs structurels
#             continue
            
#         if title in output_map:
#             out_content = output_map[title]
#             if in_content == out_content:
#                 scores.append(1.0)
#             else:
#                 ratio = difflib.SequenceMatcher(None, in_content, out_content).ratio()
#                 scores.append(ratio)
#         else:
#             # Recherche textuelle globale fallback au cas où le titre a légèrement bougé
#             matched_fallback = False
#             for out_title, out_content in output_map.items():
#                 if in_content in out_content or out_content in in_content:
#                     scores.append(difflib.SequenceMatcher(None, in_content, out_content).ratio())
#                     matched_fallback = True
#                     break
#             if not matched_fallback:
#                 scores.append(0.0)
            
#     return (sum(scores) / len(scores)) * 100 if scores else 100.0


# def extract_heuristic_questions(raw_markdown: str) -> List[str]:
#     """
#     Extrait de manière déterministe les questions réelles présentes dans le texte source
#     en cherchant les lignes contenant un point d'interrogation (?).
#     """
#     lines = raw_markdown.splitlines()
#     questions = []
#     for line in lines:
#         line = line.strip()
#         if "?" in line:
#             cleaned = re.sub(r"^[-*\s]*([Qq]uestion|[Qq])?\s*[:\-\s]*", "", line)
#             match = re.search(r"([^?]+\?)", cleaned)
#             if match:
#                 questions.append(match.group(1).strip())
#             else:
#                 questions.append(cleaned)
#     return [q for q in questions if q]


# def calculate_exr(raw_markdown: str, open_questions: List[str]) -> float:
#     """
#     Extraction Recall (ExR) :
#     Mesure la capacité du LLM à trouver et extraire toutes les questions du document.
#     """
#     gt_questions = extract_heuristic_questions(raw_markdown)
    
#     if not gt_questions:
#         return 100.0
        
#     found_count = 0
#     for gt in gt_questions:
#         for oq in open_questions:
#             if gt.lower() in oq.lower() or oq.lower() in gt.lower():
#                 found_count += 1
#                 break
#             elif difflib.SequenceMatcher(None, gt.lower(), oq.lower()).ratio() > 0.7:
#                 found_count += 1
#                 break
                
#     return (found_count / len(gt_questions)) * 100


# def calculate_gri(elements: List[Any], relationships: List[Any]) -> float:
#     """
#     Graph Relational Integrity (GRI) - NOUVELLE MÉTRIQUE FUSIONNÉE :
#     S'assure de la cohérence interne du graphe extrait. Valide que les liens 
#     pointent vers des nœuds existants dans la liste des éléments.
#     """
#     if not relationships:
#         return 100.0 # Pas de relation extraite, cohérence nominale valide
        
#     # Collecte de tous les identifiants valides et des extraits de contenus courts
#     valid_nodes = set()
#     for el in elements:
#         ident = getattr(el, "identifier", el.get("identifier"))
#         content = getattr(el, "content", el.get("content", ""))
#         if ident:
#             valid_nodes.add(str(ident).lower())
#         if content:
#             valid_nodes.add(content[:30].strip().lower()) # Ancre de contenu court

#     valid_relations = 0
#     for rel in relationships:
#         source = str(getattr(rel, "from", rel.get("from", ""))).lower()
#         target = str(getattr(rel, "to", rel.get("to", ""))).lower()
        
#         # Vérification si la source et la cible se rattachent à des entités réelles
#         source_valid = any(source in node or node in source for node in valid_nodes)
#         target_valid = any(target in node or node in target for node in valid_nodes)
        
#         if source_valid and target_valid:
#             valid_relations += 1
            
#     return (valid_relations / len(relationships)) * 100


# # ===========================================================================
# # MÉTRIQUES ADDITIONNELLES POUR LE SUMMARY AGENT
# # ===========================================================================

# def calculate_wca(executive_brief: str, min_words: int = 30, max_words: int = 150) -> float:
#     """
#     Word Count Adherence (WCA) :
#     Vérifie le respect des contraintes strictes de longueur pour le résumé exécutif.
#     Retourne 100% si la longueur est respectée, sinon applique une pénalité linéaire.
#     """
#     if not executive_brief:
#         return 0.0
    
#     words = executive_brief.split()
#     word_count = len(words)
    
#     if min_words <= word_count <= max_words:
#         return 100.0
        
#     if word_count < min_words:
#         deviation = (min_words - word_count) / min_words
#     else:
#         deviation = (word_count - max_words) / max_words
        
#     return max(0.0, (1.0 - deviation) * 100)


# def calculate_gsc(languages_and_frameworks: List[str], parsed_elements: List[Dict[str, Any]]) -> float:
#     """
#     Graph Stack Content (GSC) :
#     Mesure le taux d'alignement de la pile technique résumée par rapport aux éléments 
#     formellement identifiés par le Parsing Agent (type 'tool_configuration' ou attributs).
#     """
#     if not languages_and_frameworks:
#         return 100.0
#     if not parsed_elements:
#         return 0.0

#     valid_references = set()
#     for el in parsed_elements:
#         content = el.get("content", "").lower()
#         ident = el.get("identifier", "").lower()
#         valid_references.add(content)
#         valid_references.add(ident)
        
#         attributes = el.get("attributes", {})
#         if isinstance(attributes, dict):
#             for val in attributes.values():
#                 valid_references.add(str(val).lower())

#     matched_count = 0
#     for tech in languages_and_frameworks:
#         tech_lower = tech.lower()
#         if any(tech_lower in ref or ref in tech_lower for ref in valid_references):
#             matched_count += 1

#     return (matched_count / len(languages_and_frameworks)) * 100


# def calculate_mac(maturity_assessment: str, structural_gaps: List[Dict[str, Any]]) -> float:
#     """
#     Maturity Assessment Coherence (MAC) :
#     Évalue si la synthèse narrative prend correctement en compte les lacunes documentaires.
#     Vérifie l'analyse critique par rapport aux anomalies structurelles présentes.
#     """
#     if not structural_gaps:
#         return 100.0
#     if not maturity_assessment:
#         return 0.0

#     assessment_lower = maturity_assessment.lower()
#     matched_gaps = 0

#     for gap in structural_gaps:
#         missing_sec = gap.get("missing_section", "").lower()
#         if missing_sec in assessment_lower or any(k in assessment_lower for k in ["gap", "miss", "manqu"]):
#             matched_gaps += 1

#     return (matched_gaps / len(structural_gaps)) * 100
