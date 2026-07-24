import json
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from uuid import UUID

# Services & Tools
from app.services.parser_service import run_parsing_agent
from app.services.summary_service import SummaryAgentService
from app.services.glossary_service import GlossaryAgentService
from app.services.diagram_service import DiagramAgentService
from app.services.doc_writer_service import DocWriterAgentService
from app.services.layout_service import LayoutAgentService
from app.utils.glossary_tools import GlossaryHarvesterService
from app.utils.diagram_tools import DiagramExporterTool
from app.services.evaluation_service import DocWriterEvaluatorService
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

# NEW: Database imports
from app.database import SessionLocal
from app.models import Artifact, PipelineRun, DocVersion, Project, PipelineStage
from sqlalchemy.sql import func

# Global paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
OUTPUTS_DIR = BASE_DIR.parent / "test_files" / "outputs"


def _get_base_stem(file_name: str) -> str:
    return Path(file_name).stem


def _save_json(file_path: Path, data: Any) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        if hasattr(data, "model_dump_json"):
            f.write(data.model_dump_json(indent=4))
        else:
            json.dump(data, f, indent=4, ensure_ascii=False)


# ==============================================================================
# DB HELPER FUNCTIONS
# ==============================================================================

def _extract_kpi(report: Dict[str, Any]) -> Optional[float]:
    """
    Extract a single global KPI score (0-100) from an evaluator report.
    Tries multiple common keys, falls back to averaging available scores.
    """
    if not report or not isinstance(report, dict):
        return None
    
    # Try direct global score first
    for key in ("global_score", "overall_score", "total_score", "score"):
        if key in report and isinstance(report[key], (int, float)):
            return float(report[key])
    
    # Try health_index from parsing
    if "project_management_kpis" in report:
        kpis = report["project_management_kpis"]
        if isinstance(kpis, dict) and "health_index" in kpis:
            return float(kpis["health_index"])
    
    # Average all numeric values in technical_evaluation
    if "technical_evaluation" in report:
        tech = report["technical_evaluation"]
        if isinstance(tech, dict):
            scores = [float(v) for v in tech.values() if isinstance(v, (int, float))]
            if scores:
                return round(sum(scores) / len(scores), 1)
    
    # Average top-level numeric values
    scores = [float(v) for v in report.values() if isinstance(v, (int, float))]
    if scores:
        return round(sum(scores) / len(scores), 1)
    
    return None


def _compute_global_kpi(kpis: Dict[str, Optional[float]]) -> Optional[float]:
    """Compute weighted global KPI from individual stage KPIs."""
    weights = {
        "parsing_kpi": 0.20,
        "summary_kpi": 0.15,
        "glossary_kpi": 0.15,
        "diagram_kpi": 0.15,
        "doc_writer_kpi": 0.15,
        "layout_kpi": 0.20,
    }
    total = 0.0
    weight_sum = 0.0
    for key, weight in weights.items():
        val = kpis.get(key)
        if val is not None:
            total += val * weight
            weight_sum += weight
    return round(total / weight_sum, 1) if weight_sum > 0 else None


def _create_pipeline_run(file_name: str) -> UUID:
    """Create or reuse Artifact + create PipelineRun, return run_id."""
    db = SessionLocal()
    try:
        # Try to find existing artifact by various source_path patterns
        artifact = None
        for path_variant in [file_name, f"test_files/{file_name}", f"test_files\\{file_name}"]:
            artifact = db.query(Artifact).filter(Artifact.source_path == path_variant).first()
            if artifact:
                break

        if not artifact:
            project = db.query(Project).first()
            if not project:
                project = Project(name="Default Project")
                db.add(project)
                db.commit()
                db.refresh(project)
            
            artifact = Artifact(
                project_id=project.id,
                source_path=file_name,
                artifact_type="unknown"
            )
            db.add(artifact)
            db.commit()
            db.refresh(artifact)
        
        # Check if a pipeline run already exists for this artifact (created by upload endpoint)
        existing_run = (
            db.query(PipelineRun)
            .filter(PipelineRun.artifact_id == artifact.id)
            .order_by(PipelineRun.started_at.desc())
            .first()
        )
        if existing_run:
            run_id = existing_run.id
            print(f"[DB] Reusing existing PipelineRun {run_id} for artifact {artifact.id}")
            return run_id
        
        run = PipelineRun(artifact_id=artifact.id, current_stage=PipelineStage.parsing)
        db.add(run)
        db.commit()
        run_id = run.id
        print(f"[DB] Created PipelineRun {run_id}")
        return run_id
    except Exception as exc:
        db.rollback()
        print(f"[DB ERROR] _create_pipeline_run: {exc}")
        raise
    finally:
        db.close()


def _update_run_kpi(run_id: UUID, stage: PipelineStage, kpi_key: str, kpi_score: Optional[float]):
    """Update ONLY the KPI score for a stage. No agent outputs stored."""
    db = SessionLocal()
    try:
        run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
        if not run:
            print(f"[DB WARN] PipelineRun {run_id} not found")
            return
        
        run.current_stage = stage
        if kpi_score is not None and hasattr(run, kpi_key):
            setattr(run, kpi_key, kpi_score)
            print(f"[DB] Updated {kpi_key}={kpi_score} for run {run_id}")
        
        db.commit()
    except Exception as exc:
        db.rollback()
        print(f"[DB ERROR] _update_run_kpi: {exc}")
    finally:
        db.close()


def _finalize_run(run_id: UUID, pdf_path: str, layout_kpi: Optional[float] = None):
    """Finalize pipeline: compute global KPI, create DocVersion."""
    db = SessionLocal()
    try:
        run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
        if not run:
            return
        
        # Update layout KPI
        if layout_kpi is not None:
            run.layout_kpi = layout_kpi
        
        # Compute global KPI
        kpis = {
            "parsing_kpi": run.parsing_kpi,
            "summary_kpi": run.summary_kpi,
            "diagram_kpi": run.diagram_kpi,
            "glossary_kpi": run.glossary_kpi,
            "doc_writer_kpi": run.doc_writer_kpi,
            "layout_kpi": run.layout_kpi,
        }
        run.global_kpi = _compute_global_kpi(kpis)
        run.current_stage = PipelineStage.completed
        run.completed_at = func.now()
        
        # Create DocVersion
        version_count = db.query(DocVersion).filter(
            DocVersion.artifact_id == run.artifact_id
        ).count()
        
        doc_version = DocVersion(
            artifact_id=run.artifact_id,
            version_no=version_count + 1,
            pdf_path=pdf_path,
            pipeline_run_id=run_id,
            kpi_global_score=run.global_kpi,
            generated_by="agent"
        )
        db.add(doc_version)
        db.commit()
        
        print(f"[DB] Finalized run {run_id}: global_kpi={run.global_kpi}, pdf={pdf_path}")
        
    except Exception as exc:
        db.rollback()
        print(f"[DB ERROR] _finalize_run: {exc}")
        raise
    finally:
        db.close()


def _fail_run(run_id: UUID, error: str):
    """Mark run as failed."""
    db = SessionLocal()
    try:
        run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
        if run:
            run.current_stage = PipelineStage.failed
            db.commit()
            print(f"[DB] Marked run {run_id} as failed: {error}")
    except Exception as exc:
        db.rollback()
    finally:
        db.close()


# ==============================================================================
# 1. PARSING NODE
# ==============================================================================
def parsing_node(state: GraphState) -> Dict[str, Any]:
    print("\n[🚀 NODE] Exécution du Parsing Agent...")
    file_name = state["file_name"]
    file_content = state["file_content"]
    base_stem = _get_base_stem(file_name)
    
    # Create DB tracking
    run_id = _create_pipeline_run(file_name)
    
    try:
        parsed_doc = run_parsing_agent(file_name=file_name, file_content=file_content)
        parsed_json_dict = parsed_doc.model_dump()
        
        template_path = BASE_DIR / "app" / "resources" / "sdd_templates.json"
        template_config = {}
        if template_path.exists():
            with open(template_path, "r", encoding="utf-8") as f:
                template_config = json.load(f)
        
        # Evaluate and extract KPI only
        report = ParsingEvaluatorService.evaluate(parsed_doc, template_config)
        kpi = _extract_kpi(report)
        
        # Store ONLY KPI, not the parsed output
        _update_run_kpi(run_id, PipelineStage.parsing, "parsing_kpi", kpi)
        
        # Filesystem keeps the JSON for debugging
        _save_json(OUTPUTS_DIR / f"{base_stem}_parsed.json", parsed_doc)
        _save_json(OUTPUTS_DIR / f"{base_stem}_parsing_eval.json", report)
        
        return {
            "parsed_json_dict": parsed_json_dict,
            "parsed_doc": parsed_doc,
            "parsing_metrics": report,
            "pipeline_run_id": run_id  # Pass to next nodes
        }
        
    except Exception as exc:
        _fail_run(run_id, str(exc))
        raise


# ==============================================================================
# 2. SUMMARY NODE (Parallel A)
# ==============================================================================
def summary_node(state: GraphState) -> Dict[str, Any]:
    print("\n[🚀 NODE] Exécution du Summary Agent (Branche A)...")
    file_name = state["file_name"]
    parsed_json_dict = state["parsed_json_dict"]
    parsed_doc = state["parsed_doc"]
    base_stem = _get_base_stem(file_name)
    run_id = state.get("pipeline_run_id")
    
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
    kpi = _extract_kpi(report)
    
    # Store ONLY KPI
    if run_id:
        _update_run_kpi(run_id, PipelineStage.summary, "summary_kpi", kpi)
    
    _save_json(OUTPUTS_DIR / f"{base_stem}_summary.json", summary_doc)
    _save_json(OUTPUTS_DIR / f"{base_stem}_summary_eval.json", report)
    
    return {
        "summary_doc": summary_doc,
        "summary_metrics": report,
    }


# ==============================================================================
# 3. GLOSSARY NODE (Parallel B)
# ==============================================================================
def glossary_node(state: GraphState) -> Dict[str, Any]:
    print("\n[🚀 NODE] Exécution du Glossary Agent (Branche B)...")
    file_name = state["file_name"]
    parsed_json_dict = state["parsed_json_dict"]
    parsed_doc = state["parsed_doc"]
    base_stem = _get_base_stem(file_name)
    run_id = state.get("pipeline_run_id")
    
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
    kpi = _extract_kpi(report)
    
    # Store ONLY KPI
    if run_id:
        _update_run_kpi(run_id, PipelineStage.glossary, "glossary_kpi", kpi)
    
    _save_json(OUTPUTS_DIR / f"{base_stem}_glossary.json", glossary_doc)
    _save_json(OUTPUTS_DIR / f"{base_stem}_glossary_eval.json", report)
    
    return {
        "glossary_doc": glossary_doc,
        "glossary_metrics": report,
    }


# ==============================================================================
# 4. DIAGRAM NODE (Parallel C)
# ==============================================================================
def diagram_node(state: GraphState) -> Dict[str, Any]:
    print("\n[🚀 NODE] Exécution du Diagram Agent (Branche C)...")
    file_name = state["file_name"]
    parsed_json_dict = state["parsed_json_dict"]
    parsed_doc = state["parsed_doc"]
    base_stem = _get_base_stem(file_name)
    run_id = state.get("pipeline_run_id")
    
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
        print(f"[⚠️ WARNING] Diagram Agent failed: {exc}")
        if run_id:
            _update_run_kpi(run_id, PipelineStage.diagram, "diagram_kpi", 0.0)
        return {
            "diagram_doc": None,
            "diagram_metrics": {},
            "diagram_pdf_path": None,
        }
    
    # Filter out diagrams with invalid Mermaid syntax
    if diagram_output and diagram_output.diagrams:
        valid_diagrams = []
        for i, diag in enumerate(diagram_output.diagrams, 1):
            if DiagramExporterTool.validate_mermaid_syntax(diag.mermaid_code):
                valid_diagrams.append(diag)
                print(f"[✅] Diagramme #{i} '{diag.title}' — syntaxe valide")
            else:
                print(f"[⚠️] Diagramme #{i} '{diag.title}' — syntaxe invalide, ignoré")
        diagram_output.diagrams = valid_diagrams
    
    pdf_path_str = None
    try:
        diagrams_dict = diagram_output.model_dump()
        pdf_path = asyncio.run(DiagramExporterTool.render_diagrams_to_pdf(
            file_stem=base_stem,
            diagrams_data=diagrams_dict
        ))
        pdf_path_str = str(pdf_path)
        print(f"[📄] PDF Diagrammes généré: {pdf_path_str}")
    except Exception as exc:
        print(f"[⚠️] Erreur rendu PDF diagrammes: {exc}")
    
    report = DiagramEvaluatorService.evaluate(
        diagram_data=diagram_output,
        parsed_data=parsed_doc
    )
    kpi = _extract_kpi(report)
    
    # Store ONLY KPI
    if run_id:
        _update_run_kpi(run_id, PipelineStage.diagram, "diagram_kpi", kpi)
    
    _save_json(OUTPUTS_DIR / f"{base_stem}_diagrams.json", diagram_output)
    _save_json(OUTPUTS_DIR / f"{base_stem}_diagram_eval.json", report)
    
    return {
        "diagram_doc": diagram_output,
        "diagram_metrics": report,
        "diagram_pdf_path": pdf_path_str,
    }


# ==============================================================================
# 5. DOC WRITER NODE (Convergence)
# ==============================================================================
def doc_writer_node(state: GraphState) -> Dict[str, Any]:
    print("\n[🚀 NODE] Exécution du Documentation Writer Agent...")
    file_name = state["file_name"]
    base_stem = _get_base_stem(file_name)
    markdowns_dir = OUTPUTS_DIR / "markdowns"
    markdowns_dir.mkdir(parents=True, exist_ok=True)
    run_id = state.get("pipeline_run_id")
    
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
        
        output_md_path = markdowns_dir / f"{base_stem}_doc.md"
        with open(output_md_path, "w", encoding="utf-8") as f:
            f.write(doc_writer_output.markdown_content)
        md_path_str = str(output_md_path)
        
        fallback_diagram = diagram_doc if isinstance(diagram_doc, DiagramOutputModel) else DiagramOutputModel(**diagrams_json_dict)
        
        eval_report = DocWriterEvaluatorService.evaluate(
            markdown_text=doc_writer_output.markdown_content,
            parsed_data=parsed_doc,
            summary_data=summary_doc,
            glossary_data=glossary_doc,
            diagram_data=fallback_diagram
        )
        
        eval_json_path = markdowns_dir / f"{base_stem}_doc_eval.json"
        _save_json(eval_json_path, eval_report)
        eval_path_str = str(eval_json_path)
        
        # Extract and store ONLY KPI
        kpi = _extract_kpi(eval_report)
        if run_id:
            _update_run_kpi(run_id, PipelineStage.writing, "doc_writer_kpi", kpi)
        
    except Exception as exc:
        print(f"[❌ ERROR] DocWriterAgent: {exc}")
        if run_id:
            _fail_run(run_id, f"DocWriter: {exc}")
    
    return {
        "doc_writer_doc": doc_writer_output,
        "doc_writer_metrics": eval_report,
        "doc_writer_md_path": md_path_str,
        "doc_writer_eval_path": eval_path_str,
        "pipeline_run_id": run_id
    }


# ==============================================================================
# 6. LAYOUT NODE (Final — creates PDF + DocVersion)
# ==============================================================================
def layout_node(state: GraphState) -> Dict[str, Any]:
    print("\n[🚀 NODE] Exécution du Layout Agent (Publication PDF)...")
    file_name = state["file_name"]
    base_stem = _get_base_stem(file_name)
    documents_dir = OUTPUTS_DIR / "documents"
    documents_dir.mkdir(parents=True, exist_ok=True)
    run_id = state.get("pipeline_run_id")
    
    doc_writer_doc = state.get("doc_writer_doc")
    markdown_text = ""
    if doc_writer_doc and hasattr(doc_writer_doc, "markdown_content"):
        markdown_text = doc_writer_doc.markdown_content
    else:
        output_md_path = OUTPUTS_DIR / "markdowns" / f"{base_stem}_doc.md"
        if output_md_path.exists():
            with open(output_md_path, "r", encoding="utf-8") as f:
                markdown_text = f.read()
    
    spec_path = BASE_DIR / "app" / "resources" / "layout_spec.json"
    layout_spec_dict = {}
    if spec_path.exists():
        with open(spec_path, "r", encoding="utf-8") as f:
            layout_spec_dict = json.load(f)
    
    output_pdf_path = documents_dir / f"{base_stem}_spec.pdf"
    
    layout_result = None
    pdf_path_str = None
    
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
            print(f"[📄] PDF généré: {output_pdf_path.name}")
            
            # Extract layout KPI from technical_evaluation
            layout_kpi = None
            if layout_result.technical_evaluation:
                layout_kpi = _extract_kpi({
                    "technical_evaluation": layout_result.technical_evaluation
                })
            
            # Finalize: store KPI + create DocVersion
            if run_id:
                _finalize_run(run_id, pdf_path_str, layout_kpi)
        else:
            if run_id:
                _fail_run(run_id, "Layout agent did not generate PDF")
        
    except Exception as exc:
        print(f"[❌ ERROR] LayoutAgent: {exc}")
        if run_id:
            _fail_run(run_id, f"Layout: {exc}")
    
    return {
        "layout_doc": layout_result,
        "layout_pdf_path": pdf_path_str,
        "pipeline_run_id": run_id
    }