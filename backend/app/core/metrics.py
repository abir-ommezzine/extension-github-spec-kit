# app/core/metrics.py
"""
metrics.py — Calculateur de métriques d'évaluation pour les agents (Version Finale Unifiée).
Évalue le Parsing, la Synthèse (Summary), le Glossaire et la Modélisation Graphique (Diagrams).
"""

import re
import difflib
from typing import List, Dict, Any


# ===========================================================================
# 1. MÉTRIQUES POUR LE PARSING AGENT
# ===========================================================================

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
    altérée ou résumée.
    """
    if not input_sections:
        return 100.0
        
    input_map = {sec["title"].strip().lower(): sec["raw_content"].strip() for sec in input_sections}
    output_map = {getattr(sec, "title", sec.get("title", "")).strip().lower(): getattr(sec, "raw_content", sec.get("raw_content", "")).strip() for sec in output_sections}

    scores = []
    for title, in_content in input_map.items():
        if not in_content:
            continue
            
        if title in output_map:
            out_content = output_map[title]
            if in_content == out_content:
                scores.append(1.0)
            else:
                ratio = difflib.SequenceMatcher(None, in_content, out_content).ratio()
                scores.append(ratio)
        else:
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
    """Extrait de manière déterministe les questions réelles du texte source."""
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
    """Extraction Recall (ExR) : Mesure la capacité à extraire les questions réouvertes."""
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
    """Graph Relational Integrity (GRI) : Vérifie la validité des liens du graphe."""
    if not relationships:
        return 100.0
        
    valid_nodes = set()
    for el in elements:
        ident = getattr(el, "identifier", el.get("identifier"))
        content = getattr(el, "content", el.get("content", ""))
        if ident:
            valid_nodes.add(str(ident).lower())
        if content:
            valid_nodes.add(content[:30].strip().lower())

    valid_relations = 0
    for rel in relationships:
        source = str(getattr(rel, "from", rel.get("from", ""))).lower()
        target = str(getattr(rel, "to", rel.get("to", ""))).lower()
        
        source_valid = any(source in node or node in source for node in valid_nodes)
        target_valid = any(target in node or node in target for node in valid_nodes)
        
        if source_valid and target_valid:
            valid_relations += 1
            
    return (valid_relations / len(relationships)) * 100


# ===========================================================================
# 2. MÉTRIQUES POUR LE SUMMARY AGENT
# ===========================================================================

def calculate_wca(executive_brief: str, min_words: int = 30, max_words: int = 150) -> float:
    """Word Count Adherence (WCA) : Respect de la longueur du résumé."""
    if not executive_brief:
        return 0.0
    words = executive_brief.split()
    word_count = len(words)
    if min_words <= word_count <= max_words:
        return 100.0
    deviation = (min_words - word_count) / min_words if word_count < min_words else (word_count - max_words) / max_words
    return max(0.0, (1.0 - deviation) * 100)


def calculate_gsc(languages_and_frameworks: List[str], parsed_elements: List[Dict[str, Any]]) -> float:
    """Graph Stack Content (GSC) : Alignement de la stack avec le graphe parsé."""
    if not languages_and_frameworks:
        return 100.0
    if not parsed_elements:
        return 0.0

    valid_references = set()
    for el in parsed_elements:
        valid_references.add(el.get("content", "").lower())
        valid_references.add(el.get("identifier", "").lower())

    matched_count = sum(1 for tech in languages_and_frameworks if any(tech.lower() in ref for ref in valid_references))
    return (matched_count / len(languages_and_frameworks)) * 100


def calculate_mac(maturity_assessment: str, structural_gaps: List[Dict[str, Any]]) -> float:
    """Maturity Assessment Coherence (MAC) : Prise en compte des lacunes documentaires."""
    if not structural_gaps:
        return 100.0
    if not maturity_assessment:
        return 0.0
    assessment_lower = maturity_assessment.lower()
    matched_gaps = sum(1 for gap in structural_gaps if gap.get("missing_section", "").lower() in assessment_lower or "gap" in assessment_lower)
    return (matched_gaps / len(structural_gaps)) * 100


# ===========================================================================
# 3. MÉTRIQUES POUR LE GLOSSARY AGENT
# ===========================================================================

def calculate_ata(items: List[Dict[str, Any]]) -> float:
    """Anti-Tautology Adherence (ATA) : Taux de définitions non tautologiques."""
    if not items:
        return 100.0
    violations = sum(1 for item in items if str(item.get("term", "")).strip().lower() in str(item.get("project_definition", "")).strip().lower())
    return ((len(items) - violations) / len(items)) * 100


def calculate_cap(items: List[Dict[str, Any]], parsed_elements: List[Dict[str, Any]], parsed_sections: List[Dict[str, Any]]) -> float:
    """Contextual Anchor Precision (CAP) : Précision géométrique des ancres."""
    if not items:
        return 100.0
    valid_anchors = {str(el.get("identifier")).strip().lower() for el in parsed_elements if el.get("identifier")}
    valid_anchors.update({str(sec.get("title")).strip().lower() for sec in parsed_sections if sec.get("title")})

    matched_anchors = sum(1 for item in items if str(item.get("contextual_anchor", "")).strip().lower() in valid_anchors)
    return (matched_anchors / len(items)) * 100


# ===========================================================================
# 4. NOUVELLES MÉTRIQUES POUR LE DIAGRAM AGENT
# ===========================================================================

ALLOWED_DIAGRAM_HEADERS = {
    "flowchart", "sequencediagram", "classdiagram", "erdiagram",
    "statediagram", "gantt", "mindmap", "pie"
}

def calculate_svr(diagrams: List[Dict[str, Any]]) -> float:
    """
    Syntax Validity Rate (SVR) :
    Vérifie la validité syntaxique globale des schémas Mermaid générés.
    S'assure que le code commence par un entête valide, ne contient pas de balises
    markdown corrompues et respecte les paires de balises de nœuds.
    """
    if not diagrams:
        return 0.0

    valid_count = 0
    for diag in diagrams:
        code = str(diag.get("mermaid_code", "")).strip()
        if not code or code.startswith("```"):
            continue

        first_line = code.split("\n")[0].strip().lower()
        has_valid_header = any(first_line.startswith(h) for h in ALLOWED_DIAGRAM_HEADERS)

        # Vérification des anomalies de nœuds sans identifiant ou de crochets non fermés
        has_unmatched_brackets = code.count("[") != code.count("]") or code.count("{") != code.count("}")

        if has_valid_header and not has_unmatched_brackets:
            valid_count += 1

    return (valid_count / len(diagrams)) * 100


def calculate_dcr(diagrams: List[Dict[str, Any]], parsed_elements: List[Dict[str, Any]]) -> float:
    """
    Diagram Element Coverage Rate (DCR) - Traçabilité :
    Mesure le pourcentage d'éléments clés du graphe (Entities, Endpoints, User Stories)
    qui sont explicitement représentés dans le texte source des schémas Mermaid.
    """
    if not parsed_elements or not diagrams:
        return 100.0 if not parsed_elements else 0.0

    all_diagrams_code = " ".join(str(d.get("mermaid_code", "")).lower() for d in diagrams)

    target_elements = [
        el for el in parsed_elements 
        if el.get("type") in ["ENTITY", "ENDPOINT", "USER_STORY", "REQUIREMENT", "DATABASE", "MODEL"]
    ]

    if not target_elements:
        return 100.0

    found_count = 0
    for el in target_elements:
        ident = str(el.get("identifier", "")).lower()
        content = str(el.get("content", "")).lower()
        
        # Recherche si l'identifiant ou un extrait du contenu est présent dans un des diagrammes
        if (ident and ident in all_diagrams_code) or (content and content[:20] in all_diagrams_code):
            found_count += 1

    return (found_count / len(target_elements)) * 100


def calculate_rcr(diagrams: List[Dict[str, Any]], parsed_relationships: List[Dict[str, Any]]) -> float:
    """
    Relational Completeness Rate (RCR) :
    Mesure si les relations entre entités définies dans le graphe ('relationships')
    sont conservées et modélisées sous forme de liaisons/flèches (-->, ->>, ||--o{) dans les diagrammes.
    """
    if not parsed_relationships:
        return 100.0
    if not diagrams:
        return 0.0

    all_diagrams_code = " ".join(str(d.get("mermaid_code", "")).lower() for d in diagrams)

    matched_relations = 0
    for rel in parsed_relationships:
        source = str(rel.get("source", rel.get("from", ""))).lower()
        target = str(rel.get("to", "")).lower()

        if source and target and (source in all_diagrams_code) and (target in all_diagrams_code):
            matched_relations += 1

    return (matched_relations / len(parsed_relationships)) * 100


def calculate_sra(diagrams: List[Dict[str, Any]]) -> float:
    """
    Structural Rule Adherence (SRA) :
    Évalue le respect des contraintes structurelles de la spécification :
    1. Pour les 'flowchart' : Vérifie la présence de losanges de décision '{?}' (non-linéarité).
    2. Pour les 'erDiagram' : Vérifie l'absence de notation UML incompatible (ex: +field: type).
    """
    if not diagrams:
        return 100.0

    compliant_diagrams = 0
    for diag in diagrams:
        code = str(diag.get("mermaid_code", "")).strip()
        diag_type = str(diag.get("type", "")).lower()

        if "flowchart" in diag_type:
            # Règle de non-linéarité : doit contenir au moins un losange de décision {?}
            has_decision = "{" in code and "}" in code
            if has_decision:
                compliant_diagrams += 1
        elif "erdiagram" in diag_type:
            # Règle d'attribut ER : ne doit pas contenir de notation UML de type '+id:'
            has_uml_notation = bool(re.search(r'\+\s*\w+\s*:', code))
            if not has_uml_notation:
                compliant_diagrams += 1
        else:
            compliant_diagrams += 1

    return (compliant_diagrams / len(diagrams)) * 100
