# app/graph/nodes.py
import json
import asyncio
from pathlib import Path
from typing import Dict, Any
from typing import Type, TypeVar
from pydantic import BaseModel
import re
# Services & Outils
from app.services.parser_service import run_parsing_agent
from app.services.summary_service import SummaryAgentService
from app.services.glossary_service import GlossaryAgentService
from app.services.diagram_service import DiagramAgentService
from app.utils.glossary_tools import GlossaryHarvesterService
from app.utils.diagram_tools import DiagramExporterTool

# Evaluators
from app.services.evaluation_service import (
    ParsingEvaluatorService,
    SummaryEvaluatorService,
    GlossaryEvaluatorService,
    DiagramEvaluatorService
)

# Schemas
from app.schemas.parsing_agent_schema import ParsingAgentOutput
from app.graph.state import GraphState

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
OUTPUTS_DIR = BASE_DIR.parent / "test_files" / "outputs"


def _get_base_stem(file_name: str) -> str:
    """Extrait le nom de base du fichier sans son extension (ex: 'requirements(1).md' -> 'requirements(1)')."""
    return Path(file_name).stem


def _save_json(file_path: Path, data: Any) -> None:
    """Utilitaire pour sauvegarder un dictionnaire ou un modèle Pydantic au format JSON."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        if hasattr(data, "model_dump_json"):
            f.write(data.model_dump_json(indent=4))
        else:
            json.dump(data, f, indent=4, ensure_ascii=False)


# ------------------------------------------------------------------------------
# 1. PARSING NODE
# ------------------------------------------------------------------------------
def parsing_node(state: GraphState) -> Dict[str, Any]:
    print("\n[🚀 NODE] Exécution du Parsing Agent...")
    file_name = state["file_name"]
    file_content = state["file_content"]
    base_stem = _get_base_stem(file_name)
    
    parsed_doc = run_parsing_agent(file_name=file_name, file_content=file_content)
    parsed_json_dict = parsed_doc.model_dump()
    
    template_path = BASE_DIR / "app" / "resources" / "sdd_templates.json"
    template_config = {}
    if template_path.exists():
        with open(template_path, "r", encoding="utf-8") as f:
            template_config = json.load(f)
            
    report = ParsingEvaluatorService.evaluate(parsed_doc, template_config)
    
    _save_json(OUTPUTS_DIR / f"{base_stem}_parsed.json", parsed_doc)
    _save_json(OUTPUTS_DIR / f"{base_stem}_parsing_eval.json", report)
    print(f"[💾] Enregistré : {base_stem}_parsed.json & {base_stem}_parsing_eval.json")
    
    return {
        "parsed_json_dict": parsed_json_dict,
        "parsed_doc": parsed_doc,
        "parsing_metrics": report
    }


# ------------------------------------------------------------------------------
# 2. SUMMARY NODE (Exécution Parallèle A)
# ------------------------------------------------------------------------------
def summary_node(state: GraphState) -> Dict[str, Any]:
    print("\n[🚀 NODE] Exécution du Summary Agent (Branche A)...")
    file_name = state["file_name"]
    parsed_json_dict = state["parsed_json_dict"]
    parsed_doc = state["parsed_doc"]
    base_stem = _get_base_stem(file_name)
    
    spec_path = BASE_DIR / "app" / "resources" / "summary_spec.json"
    summary_spec_dict = {}
    if spec_path.exists():
        with open(spec_path, "r", encoding="utf-8") as f:
            summary_spec_dict = json.load(f)

    agent_service = SummaryAgentService()
    summary_doc = agent_service.generate_summary(
        parsed_json_dict=parsed_json_dict,
        summary_spec_dict=summary_spec_dict
    )
    
    report = SummaryEvaluatorService.evaluate(summary_doc, parsed_doc)
    
    _save_json(OUTPUTS_DIR / f"{base_stem}_summary.json", summary_doc)
    _save_json(OUTPUTS_DIR / f"{base_stem}_summary_eval.json", report)
    print(f"[💾] Enregistré : {base_stem}_summary.json & {base_stem}_summary_eval.json")
    
    return {
        "summary_doc": summary_doc,
        "summary_metrics": report
    }


# ------------------------------------------------------------------------------
# 3. GLOSSARY NODE (Exécution Parallèle B)
# ------------------------------------------------------------------------------
def glossary_node(state: GraphState) -> Dict[str, Any]:
    print("\n[🚀 NODE] Exécution du Glossary Agent (Branche B)...")
    file_name = state["file_name"]
    parsed_json_dict = state["parsed_json_dict"]
    parsed_doc = state["parsed_doc"]
    base_stem = _get_base_stem(file_name)
    
    spec_path = BASE_DIR / "app" / "resources" / "glossary_spec.json"
    glossary_spec_dict = {}
    if spec_path.exists():
        with open(spec_path, "r", encoding="utf-8") as f:
            glossary_spec_dict = json.load(f)

    valid_anchors = GlossaryHarvesterService.generate_and_cache_anchors(parsed_json_dict)
    candidate_terms = GlossaryHarvesterService.harvest_candidates(parsed_json_dict)

    agent_service = GlossaryAgentService()
    glossary_doc = agent_service.generate_glossary(
        parsed_json_dict=parsed_json_dict,
        glossary_spec_dict=glossary_spec_dict,
        valid_anchors=valid_anchors
    )
    
    report = GlossaryEvaluatorService.evaluate(glossary_doc, parsed_doc, candidate_terms)
    
    _save_json(OUTPUTS_DIR / f"{base_stem}_glossary.json", glossary_doc)
    _save_json(OUTPUTS_DIR / f"{base_stem}_glossary_eval.json", report)
    print(f"[💾] Enregistré : {base_stem}_glossary.json & {base_stem}_glossary_eval.json")
    
    return {
        "glossary_doc": glossary_doc,
        "glossary_metrics": report
    }


# ------------------------------------------------------------------------------
# 4. DIAGRAM NODE (Exécution Parallèle C)
# ------------------------------------------------------------------------------
# app/graph/nodes.py (extrait pour diagram_node)

def diagram_node(state: GraphState) -> Dict[str, Any]:
    """
    Nœud 4 : Exécute le Diagram Agent. En cas d'échec sur le JSON de diagramme,
    le workflow ne plante pas et poursuit son exécution.
    """
    print("\n[🚀 NODE] Exécution du Diagram Agent (Branche C)...")
    file_name = state["file_name"]
    parsed_json_dict = state["parsed_json_dict"]
    parsed_doc = state["parsed_doc"]
    base_stem = _get_base_stem(file_name)
    
    spec_path = BASE_DIR / "app" / "resources" / "diagram_spec.json"
    diagram_spec_dict = {}
    if spec_path.exists():
        with open(spec_path, "r", encoding="utf-8") as f:
            diagram_spec_dict = json.load(f)

    agent_service = DiagramAgentService()
    diagram_output = None
    
    try:
        # Inférence LLM
        diagram_output = agent_service.generate_diagrams(
            parsed_json_dict=parsed_json_dict,
            diagram_spec_dict=diagram_spec_dict
        )
    except Exception as exc:
        print(f"[⚠️ WARNING] Le Diagram Agent n'a pas pu valider son JSON : {exc}")
        print("[ℹ️] Poursuite du workflow sans interrompre les autres agents.")
        return {
            "diagram_doc": None,
            "diagram_metrics": {},
            "diagram_pdf_path": None
        }

    # Rendu PDF et Sauvegarde uniquement si le diagram_json est valide
    pdf_path_str = None
    try:
        diagrams_dict = diagram_output.model_dump()
        pdf_path = asyncio.run(DiagramExporterTool.render_diagrams_to_pdf(
            file_stem=base_stem,
            diagrams_data=diagrams_dict
        ))
        pdf_path_str = str(pdf_path)
        print(f"[📄] PDF Diagrammes généré avec succès : {pdf_path_str}")
    except Exception as exc:
        print(f"[⚠️] Erreur lors du rendu PDF : {exc}")

    # Évaluation des métriques
    report = DiagramEvaluatorService.evaluate(
        diagram_data=diagram_output,
        parsed_data=parsed_doc
    )
    
    _save_json(OUTPUTS_DIR / f"{base_stem}_diagrams.json", diagram_output)
    _save_json(OUTPUTS_DIR / f"{base_stem}_diagram_eval.json", report)
    print(f"[💾] Enregistré : {base_stem}_diagrams.json & {base_stem}_diagram_eval.json")
    
    return {
        "diagram_doc": diagram_output,
        "diagram_metrics": report,
        "diagram_pdf_path": pdf_path_str
    }
# def diagram_node(state: GraphState) -> Dict[str, Any]:
#     """
#     Nœud 4 : Exécute le Diagram Agent, génère les diagrammes Mermaid,
#     compile le PDF et évalue la qualité du rendu.
#     """
#     print("\n[🚀 NODE] Exécution du Diagram Agent (Branche C)...")
#     file_name = state["file_name"]
#     parsed_json_dict = state["parsed_json_dict"]
#     parsed_doc = state["parsed_doc"]
#     base_stem = _get_base_stem(file_name)
    
#     # Chargement de la spec diagrammes
#     spec_path = BASE_DIR / "app" / "resources" / "diagram_spec.json"
#     diagram_spec_dict = {}
#     if spec_path.exists():
#         with open(spec_path, "r", encoding="utf-8") as f:
#             diagram_spec_dict = json.load(f)

#     # Inférence LLM
#     agent_service = DiagramAgentService()
#     diagram_output = agent_service.generate_diagrams(
#         parsed_json_dict=parsed_json_dict,
#         diagram_spec_dict=diagram_spec_dict
#     )

#     # Rendu et génération du PDF
#     pdf_path_str = None
#     try:
#         diagrams_dict = diagram_output.model_dump()
#         pdf_path = asyncio.run(DiagramExporterTool.render_diagrams_to_pdf(
#             file_stem=base_stem,
#             diagrams_data=diagrams_dict
#         ))
#         pdf_path_str = str(pdf_path)
#         print(f"[📄] PDF Diagrammes généré avec succès : {pdf_path_str}")
#     except Exception as exc:
#         print(f"[⚠️] Erreur lors du rendu PDF des diagrammes : {exc}")

#     # Évaluation des métriques
#     report = DiagramEvaluatorService.evaluate(
#         diagram_data=diagram_output,
#         parsed_data=parsed_doc
#     )
    
#     # Sauvegarde sur disque
#     _save_json(OUTPUTS_DIR / f"{base_stem}_diagrams.json", diagram_output)
#     _save_json(OUTPUTS_DIR / f"{base_stem}_diagram_eval.json", report)
#     print(f"[💾] Enregistré : {base_stem}_diagrams.json & {base_stem}_diagram_eval.json")
    
#     return {
#         "diagram_doc": diagram_output,
#         "diagram_metrics": report,
#         "diagram_pdf_path": pdf_path_str
#     }
# # app/graph/nodes.py
# import json
# from pathlib import Path
# from typing import Dict, Any

# # Services & Outils
# from app.services.parser_service import run_parsing_agent
# from app.services.summary_service import SummaryAgentService
# from app.services.glossary_service import GlossaryAgentService
# from app.utils.glossary_tools import GlossaryHarvesterService

# # Evaluators
# from app.services.evaluation_service import (
#     ParsingEvaluatorService,
#     SummaryEvaluatorService,
#     GlossaryEvaluatorService
# )

# # Schemas
# from app.schemas.parsing_agent_schema import ParsingAgentOutput
# from app.graph.state import GraphState

# BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
# OUTPUTS_DIR = BASE_DIR.parent / "test_files" / "outputs"


# def _get_base_stem(file_name: str) -> str:
#     """Extrait le nom de base du fichier sans son extension (ex: 'requirements(1).md' -> 'requirements(1)')."""
#     return Path(file_name).stem


# def _save_json(file_path: Path, data: Any) -> None:
#     """Utilitaire pour sauvegarder un dictionnaire ou un modèle Pydantic au format JSON."""
#     file_path.parent.mkdir(parents=True, exist_ok=True)
#     with open(file_path, "w", encoding="utf-8") as f:
#         if hasattr(data, "model_dump_json"):
#             f.write(data.model_dump_json(indent=4))
#         else:
#             json.dump(data, f, indent=4, ensure_ascii=False)


# # ------------------------------------------------------------------------------
# # 1. PARSING NODE
# # ------------------------------------------------------------------------------
# def parsing_node(state: GraphState) -> Dict[str, Any]:
#     """
#     Nœud 1 : Exécute le Parsing Agent, sauvegarde le JSON généré + son rapport d'évaluation.
#     """
#     print("\n[🚀 NODE] Exécution du Parsing Agent...")
#     file_name = state["file_name"]
#     file_content = state["file_content"]
#     base_stem = _get_base_stem(file_name)
    
#     # Execution LLM
#     parsed_doc = run_parsing_agent(file_name=file_name, file_content=file_content)
#     parsed_json_dict = parsed_doc.model_dump()
    
#     # Evaluation
#     template_path = BASE_DIR / "app" / "resources" / "sdd_templates.json"
#     template_config = {}
#     if template_path.exists():
#         with open(template_path, "r", encoding="utf-8") as f:
#             template_config = json.load(f)
            
#     report = ParsingEvaluatorService.evaluate(parsed_doc, template_config)
    
#     # --- SAUVEGARDE EN DISQUE (JSON Généré + Rapport Évaluation) ---
#     _save_json(OUTPUTS_DIR / f"{base_stem}_parsed.json", parsed_doc)
#     _save_json(OUTPUTS_DIR / f"{base_stem}_parsing_eval.json", report)
#     print(f"[💾] Enregistré : {base_stem}_parsed.json & {base_stem}_parsing_eval.json")
    
#     return {
#         "parsed_json_dict": parsed_json_dict,
#         "parsed_doc": parsed_doc,
#         "parsing_metrics": report
#     }


# # ------------------------------------------------------------------------------
# # 2. SUMMARY NODE (Exécution Parallèle A)
# # ------------------------------------------------------------------------------
# def summary_node(state: GraphState) -> Dict[str, Any]:
#     """
#     Nœud 2 : Exécute le Summary Agent, sauvegarde le JSON généré + son rapport d'évaluation.
#     """
#     print("\n[🚀 NODE] Exécution du Summary Agent (Branche A)...")
#     file_name = state["file_name"]
#     parsed_json_dict = state["parsed_json_dict"]
#     parsed_doc = state["parsed_doc"]
#     base_stem = _get_base_stem(file_name)
    
#     # Chargement de la spec
#     spec_path = BASE_DIR / "app" / "resources" / "summary_spec.json"
#     summary_spec_dict = {}
#     if spec_path.exists():
#         with open(spec_path, "r", encoding="utf-8") as f:
#             summary_spec_dict = json.load(f)

#     # Execution LLM
#     agent_service = SummaryAgentService()
#     summary_doc = agent_service.generate_summary(
#         parsed_json_dict=parsed_json_dict,
#         summary_spec_dict=summary_spec_dict
#     )
    
#     # Evaluation
#     report = SummaryEvaluatorService.evaluate(summary_doc, parsed_doc)
    
#     # --- SAUVEGARDE EN DISQUE (JSON Généré + Rapport Évaluation) ---
#     _save_json(OUTPUTS_DIR / f"{base_stem}_summary.json", summary_doc)
#     _save_json(OUTPUTS_DIR / f"{base_stem}_summary_eval.json", report)
#     print(f"[💾] Enregistré : {base_stem}_summary.json & {base_stem}_summary_eval.json")
    
#     return {
#         "summary_doc": summary_doc,
#         "summary_metrics": report
#     }


# # ------------------------------------------------------------------------------
# # 3. GLOSSARY NODE (Exécution Parallèle B)
# # ------------------------------------------------------------------------------
# def glossary_node(state: GraphState) -> Dict[str, Any]:
#     """
#     Nœud 3 : Génère les ancres, exécute le Glossary Agent, sauvegarde le JSON généré + son rapport d'évaluation.
#     """
#     print("\n[🚀 NODE] Exécution du Glossary Agent (Branche B)...")
#     file_name = state["file_name"]
#     parsed_json_dict = state["parsed_json_dict"]
#     parsed_doc = state["parsed_doc"]
#     base_stem = _get_base_stem(file_name)
    
#     # Chargement de la spec
#     spec_path = BASE_DIR / "app" / "resources" / "glossary_spec.json"
#     glossary_spec_dict = {}
#     if spec_path.exists():
#         with open(spec_path, "r", encoding="utf-8") as f:
#             glossary_spec_dict = json.load(f)

#     # Pré-traitement Harvester & Cache
#     valid_anchors = GlossaryHarvesterService.generate_and_cache_anchors(parsed_json_dict)
#     candidate_terms = GlossaryHarvesterService.harvest_candidates(parsed_json_dict)

#     # Execution LLM
#     agent_service = GlossaryAgentService()
#     glossary_doc = agent_service.generate_glossary(
#         parsed_json_dict=parsed_json_dict,
#         glossary_spec_dict=glossary_spec_dict,
#         valid_anchors=valid_anchors
#     )
    
#     # Evaluation
#     report = GlossaryEvaluatorService.evaluate(glossary_doc, parsed_doc, candidate_terms)
    
#     # --- SAUVEGARDE EN DISQUE (JSON Généré + Rapport Évaluation) ---
#     _save_json(OUTPUTS_DIR / f"{base_stem}_glossary.json", glossary_doc)
#     _save_json(OUTPUTS_DIR / f"{base_stem}_glossary_eval.json", report)
#     print(f"[💾] Enregistré : {base_stem}_glossary.json & {base_stem}_glossary_eval.json")
    
#     return {
#         "glossary_doc": glossary_doc,
#         "glossary_metrics": report
#     }
