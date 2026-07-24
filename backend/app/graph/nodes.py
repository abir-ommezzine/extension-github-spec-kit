import json
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

# Services & Outils
from app.services.parser_service import run_parsing_agent
from app.services.summary_service import SummaryAgentService
from app.services.glossary_service import GlossaryAgentService
from app.services.diagram_service import DiagramAgentService
from app.services.doc_writer_service import DocWriterAgentService
from app.services.layout_service import LayoutAgentService
from app.utils.glossary_tools import GlossaryHarvesterService
from app.utils.diagram_tools import DiagramExporterTool

# Evaluators
from app.services.evaluation_service import (
    ParsingEvaluatorService,
    SummaryEvaluatorService,
    GlossaryEvaluatorService,
    DiagramEvaluatorService,
    DocWriterEvaluatorService
)

# Schemas & State
from app.schemas.parsing_agent_schema import ParsingAgentOutput
from app.schemas.diagram_agent_schema import DiagramOutputModel
from app.schemas.layout_agent_schema import LayoutOutputModel
from app.graph.state import GraphState

# ------------------------------------------------------------------------------
# Définition des Chemins Globaux (Option A)
# ------------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
PROJECT_ROOT = BASE_DIR.parent                             # Racine StageTalan/

# Dossier Mère outputs/ au même niveau que test_files/ et backend/
OUTPUTS_DIR = PROJECT_ROOT / "outputs"

DOCUMENTS_DIR = OUTPUTS_DIR / "documents"     # .md et .pdf
DATA_DIR = OUTPUTS_DIR / "data"               # .json outputs
EVALUATIONS_DIR = OUTPUTS_DIR / "evaluations" # .json evaluations
DIAGRAMS_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "data" / "diagrams"

def _get_base_stem(file_name: str) -> str:
    """Extrait le nom de base du fichier sans son extension."""
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
    
    # Données dans /data, Évaluation dans /evaluations
    _save_json(DATA_DIR / f"{base_stem}_parsed.json", parsed_doc)
    _save_json(EVALUATIONS_DIR / f"{base_stem}_parsing_eval.json", report)
    print(f"[💾] Enregistré : {base_stem}_parsed.json (data/) & {base_stem}_parsing_eval.json (evaluations/)")
    
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
    
    _save_json(DATA_DIR / f"{base_stem}_summary.json", summary_doc)
    _save_json(EVALUATIONS_DIR / f"{base_stem}_summary_eval.json", report)
    print(f"[💾] Enregistré : {base_stem}_summary.json (data/) & {base_stem}_summary_eval.json (evaluations/)")
    
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
    
    _save_json(DATA_DIR / f"{base_stem}_glossary.json", glossary_doc)
    _save_json(EVALUATIONS_DIR / f"{base_stem}_glossary_eval.json", report)
    print(f"[💾] Enregistré : {base_stem}_glossary.json (data/) & {base_stem}_glossary_eval.json (evaluations/)")
    
    return {
        "glossary_doc": glossary_doc,
        "glossary_metrics": report
    }


# ------------------------------------------------------------------------------
# 4. DIAGRAM NODE (Exécution Parallèle C)
# ------------------------------------------------------------------------------
def diagram_node(state: GraphState) -> Dict[str, Any]:
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
        diagram_output = agent_service.generate_diagrams(
            parsed_json_dict=parsed_json_dict,
            diagram_spec_dict=diagram_spec_dict
        )
    except Exception as exc:
        print(f"[⚠️ WARNING] Le Diagram Agent n'a pas pu valider son JSON : {exc}")
        return {
            "diagram_doc": None,
            "diagram_metrics": {},
            "diagram_pdf_path": None
        }

    pdf_path_str = None
    try:
        diagrams_dict = diagram_output.model_dump()
        
        # 🎯 MODIFICATION : Envoi du PDF vers outputs/data/diagrams/
        pdf_path = asyncio.run(DiagramExporterTool.render_diagrams_to_pdf(
            file_stem=base_stem,
            diagrams_data=diagrams_dict,
            output_dir=DIAGRAMS_OUTPUT_DIR  # <--- Remplacement de DOCUMENTS_DIR par DIAGRAMS_OUTPUT_DIR
        ))
        pdf_path_str = str(pdf_path)
        print(f"[📄] PDF Diagrammes généré avec succès dans data/diagrams/ : {pdf_path_str}")
    except Exception as exc:
        print(f"[⚠️] Erreur lors du rendu PDF : {exc}")

    report = DiagramEvaluatorService.evaluate(
        diagram_data=diagram_output,
        parsed_data=parsed_doc
    )
    
    _save_json(DATA_DIR / f"{base_stem}_diagrams.json", diagram_output)
    _save_json(EVALUATIONS_DIR / f"{base_stem}_diagram_eval.json", report)
    print(f"[💾] Enregistré : {base_stem}_diagrams.json (data/) & {base_stem}_diagram_eval.json (evaluations/)")
    
    return {
        "diagram_doc": diagram_output,
        "diagram_metrics": report,
        "diagram_pdf_path": pdf_path_str
    }
# ------------------------------------------------------------------------------
# 5. DOC WRITER NODE (Convergence Finale)
# ------------------------------------------------------------------------------
def doc_writer_node(state: GraphState) -> Dict[str, Any]:
    print("\n[🚀 NODE] Exécution du Documentation Writer Agent (Convergence)...")
    file_name = state["file_name"]
    base_stem = _get_base_stem(file_name)

    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    EVALUATIONS_DIR.mkdir(parents=True, exist_ok=True)

    parsed_json_dict = state.get("parsed_json_dict") or {}
    parsed_doc = state.get("parsed_doc")
    
    summary_doc = state.get("summary_doc")
    summary_json_dict = summary_doc.model_dump() if hasattr(summary_doc, "model_dump") else (summary_doc or {})
    
    glossary_doc = state.get("glossary_doc")
    glossary_json_dict = glossary_doc.model_dump() if hasattr(glossary_doc, "model_dump") else (glossary_doc or {})
    
    diagram_doc = state.get("diagram_doc")
    if diagram_doc and hasattr(diagram_doc, "model_dump"):
        diagrams_json_dict = diagram_doc.model_dump()
    elif isinstance(diagram_doc, dict):
        diagrams_json_dict = diagram_doc
    else:
        diagrams_json_dict = {"project_name": base_stem, "diagrams": []}

    spec_path = BASE_DIR / "app" / "resources" / "doc_writer_spec.json"
    doc_writer_spec_dict = {}
    if spec_path.exists():
        with open(spec_path, "r", encoding="utf-8") as f:
            doc_writer_spec_dict = json.load(f)

    service = DocWriterAgentService()
    doc_writer_output = None
    eval_report = {}
    md_path_str = None
    eval_path_str = None

    try:
        doc_writer_output = service.generate_documentation(
            parsed_json_dict=parsed_json_dict,
            summary_json_dict=summary_json_dict,
            glossary_json_dict=glossary_json_dict,
            diagrams_json_dict=diagrams_json_dict,
            doc_writer_spec_dict=doc_writer_spec_dict
        )

        # Enregistrement du fichier .md dans documents/
        output_md_path = DOCUMENTS_DIR / f"{base_stem}_doc.md"
        with open(output_md_path, "w", encoding="utf-8") as f:
            f.write(doc_writer_output.markdown_content)
        md_path_str = str(output_md_path)
        print(f"[💾] Markdown généré enregistré dans documents/ : {output_md_path.name}")

        fallback_diagram = diagram_doc if isinstance(diagram_doc, DiagramOutputModel) else DiagramOutputModel(**diagrams_json_dict)

        eval_report = DocWriterEvaluatorService.evaluate(
            markdown_text=doc_writer_output.markdown_content,
            parsed_data=parsed_doc,
            summary_data=summary_doc,
            glossary_data=glossary_doc,
            diagram_data=fallback_diagram
        )

        # Enregistrement de l'évaluation dans evaluations/
        eval_json_path = EVALUATIONS_DIR / f"{base_stem}_doc_eval.json"
        _save_json(eval_json_path, eval_report)
        eval_path_str = str(eval_json_path)
        print(f"[💾] Évaluation Markdown enregistrée dans evaluations/ : {eval_json_path.name}")

    except Exception as exc:
        print(f"[❌ ERROR] Échec lors de l'exécution du DocWriterAgent : {exc}")

    return {
        "doc_writer_doc": doc_writer_output,
        "doc_writer_metrics": eval_report,
        "doc_writer_md_path": md_path_str,
        "doc_writer_eval_path": eval_path_str
    }


# ------------------------------------------------------------------------------
# 6. LAYOUT NODE (Certification & Rendu PDF Final)
# ------------------------------------------------------------------------------
def layout_node(state: GraphState) -> Dict[str, Any]:
    print("\n[🚀 NODE] Exécution du Layout Agent (Publication PDF & Évaluation)...")
    file_name = state["file_name"]
    base_stem = _get_base_stem(file_name)
    
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    EVALUATIONS_DIR.mkdir(parents=True, exist_ok=True)

    doc_writer_doc = state.get("doc_writer_doc")
    markdown_text = ""
    if doc_writer_doc and hasattr(doc_writer_doc, "markdown_content"):
        markdown_text = doc_writer_doc.markdown_content
    else:
        output_md_path = DOCUMENTS_DIR / f"{base_stem}_doc.md"
        if output_md_path.exists():
            with open(output_md_path, "r", encoding="utf-8") as f:
                markdown_text = f.read()

    spec_path = BASE_DIR / "app" / "resources" / "layout_spec.json"
    layout_spec_dict = {}
    if spec_path.exists():
        with open(spec_path, "r", encoding="utf-8") as f:
            layout_spec_dict = json.load(f)

    # PDF Final dans documents/ et Évaluation dans evaluations/
    output_pdf_path = DOCUMENTS_DIR / f"{base_stem}_spec.pdf"
    eval_json_path = EVALUATIONS_DIR / f"{base_stem}_layout_eval.json"

    layout_result = None
    eval_report = {}
    pdf_path_str = None
    eval_path_str = None

    try:
        service = LayoutAgentService()
        layout_result = service.process_layout_and_render(
            markdown_text=markdown_text,
            layout_spec_dict=layout_spec_dict,
            project_name=base_stem,
            output_pdf_path=str(output_pdf_path)
        )

        if layout_result and layout_result.pdf_generated:
            pdf_path_str = str(output_pdf_path)
            print(f"[📄] Document PDF généré avec succès dans documents/ : {output_pdf_path.name}")
            
            eval_report = {
                "project_name": layout_result.project_name,
                "layout_publication_status": str(
                    layout_result.layout_publication_status.value 
                    if hasattr(layout_result.layout_publication_status, 'value') 
                    else layout_result.layout_publication_status
                ),
                "page_count": layout_result.page_count,
                "file_size_kb": layout_result.file_size_kb,
                "rendered_diagrams_count": layout_result.rendered_diagrams_count,
                "technical_evaluation": layout_result.technical_evaluation,
                "project_management_kpis": layout_result.project_management_kpis,
                "execution_warnings": layout_result.execution_warnings
            }

            _save_json(eval_json_path, eval_report)
            eval_path_str = str(eval_json_path)
            print(f"[💾] Évaluation Layout JSON enregistrée dans evaluations/ : {eval_json_path.name}")

    except Exception as exc:
        print(f"[❌ ERROR] Échec lors de l'exécution du LayoutAgent : {exc}")

    return {
        "layout_doc": layout_result,
        "layout_metrics": eval_report,
        "layout_pdf_path": pdf_path_str,
        "layout_eval_path": eval_path_str
    }
