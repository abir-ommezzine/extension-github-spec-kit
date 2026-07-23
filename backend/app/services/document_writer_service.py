# app/services/document_writer_service.py

import json
from typing import Dict, Any, Optional, List
from pathlib import Path

from app.schemas.document_writer_schema import DocumentWriterOutput
from app.schemas.summary_agent_schema import SummaryOutputModel
from app.schemas.glossary_agent_schema import GlossaryOutputModel
from app.schemas.parsing_agent_schema import ParsingAgentOutput
from app.core.prompts import get_doc_writer_prompt
from app.core.llm_client import ollama_chat, get_llm_model
from app.core.llm_utils import parse_and_validate_json


class DocumentWriterService:
    """
    Service d'orchestration pour le Document Writer Agent.
    Consolide les sorties des agents parallèles via l'API Groq.
    """

    def generate_document(
        self,
        parsed_json_dict: Dict[str, Any],
        parsed_doc: ParsingAgentOutput,
        summary_doc: Optional[SummaryOutputModel],
        glossary_doc: Optional[GlossaryOutputModel],
        diagram_doc: Optional[Any],
        diagram_pdf_path: Optional[str],
        document_spec_dict: Dict[str, Any]
    ) -> DocumentWriterOutput:
        """
        Exécute le pipeline complet du Document Writer Agent via Groq.
        """
        print("[📝] Document Writer — Préparation du payload consolidé...")

        # 1. Construction du payload
        consolidated_payload = self._build_consolidated_payload(
            parsed_json_dict=parsed_json_dict,
            parsed_doc=parsed_doc,
            summary_doc=summary_doc,
            glossary_doc=glossary_doc,
            diagram_doc=diagram_doc,
            diagram_pdf_path=diagram_pdf_path,
            document_spec=document_spec_dict
        )

        # 2. Prompts
        system_prompt = get_doc_writer_prompt()
        user_prompt = json.dumps(consolidated_payload, ensure_ascii=False, indent=2)

        # 3. Appel Groq
        print(f"[🤖] Document Writer — Appel Groq (modèle: {get_llm_model()})...")
        print("   ⏳ Cela peut prendre 5-15 secondes...")
        
        response = ollama_chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=8192  # Groq supports up to 8192 for this model
        )

        raw_output = response

        # 4. Validation Pydantic
        document_output = parse_and_validate_json(raw_output, DocumentWriterOutput)

        # 5. Post-traitement
        document_output.word_count = len(document_output.markdown_content.split())
        if glossary_doc and glossary_doc.items:
            document_output.glossary_term_count = len(glossary_doc.items)
        if diagram_doc and hasattr(diagram_doc, 'diagrams'):
            document_output.diagram_count = len(diagram_doc.diagrams)

        print(f"[✅] Document Writer — Document généré : {document_output.word_count} mots, "
              f"{document_output.diagram_count} diagrammes, {document_output.glossary_term_count} termes.")

        return document_output
    
    def _build_consolidated_payload(
        self,
        parsed_json_dict: Dict[str, Any],
        parsed_doc: ParsingAgentOutput,
        summary_doc: Optional[SummaryOutputModel],
        glossary_doc: Optional[GlossaryOutputModel],
        diagram_doc: Optional[Any],
        diagram_pdf_path: Optional[str],
        document_spec: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Assemble un payload JSON structuré contenant toutes les données des agents
        prêtes à être synthétisées par le LLM.
        """
        payload = {
            "document_specification": document_spec,
            "project_metadata": {
                "project_name": parsed_doc.project_info.get("project_name", "Unknown Project"),
                "doc_type": parsed_doc.doc_type.value,
                "brief_explanation": parsed_doc.project_info.get("brief_explanation", "")
            },
            "sources": {
                "parsing": {
                    "available": True,
                    "sections_count": len(parsed_doc.sections),
                    "elements_count": len(parsed_doc.elements),
                    "relationships_count": len(parsed_doc.relationships),
                    "structural_gaps": [
                        {"missing": g.missing_section, "priority": g.priority}
                        for g in parsed_doc.structural_gaps
                    ],
                    "open_questions": parsed_doc.open_questions
                },
                "summary": {
                    "available": summary_doc is not None,
                    "data": summary_doc.model_dump() if summary_doc else None
                },
                "glossary": {
                    "available": glossary_doc is not None,
                    "term_count": len(glossary_doc.items) if glossary_doc else 0,
                    "items": [
                        {
                            "term": item.term,
                            "category": item.category.value,
                            "definition": item.project_definition,
                            "anchor": item.contextual_anchor
                        }
                        for item in (glossary_doc.items if glossary_doc else [])
                    ]
                },
                "diagrams": {
                    "available": diagram_doc is not None,
                    "pdf_path": diagram_pdf_path,
                    "mermaid_diagrams": self._extract_mermaid_diagrams(diagram_doc) if diagram_doc else []
                }
            }
        }
        return payload

    def _extract_mermaid_diagrams(self, diagram_doc: Any) -> List[Dict[str, str]]:
        """
        Extrait les diagrammes Mermaid bruts du diagram_doc pour intégration inline.
        """
        diagrams = []
        if hasattr(diagram_doc, 'diagrams') and diagram_doc.diagrams:
            for diag in diagram_doc.diagrams:
                diagrams.append({
                    "title": getattr(diag, 'title', 'Untitled Diagram'),
                    "type": getattr(diag, 'type', 'flowchart'),
                    "description": getattr(diag, 'description', ''),
                    "mermaid_code": getattr(diag, 'mermaid_code', '')
                })
        elif isinstance(diagram_doc, dict) and 'diagrams' in diagram_doc:
            for diag in diagram_doc['diagrams']:
                diagrams.append({
                    "title": diag.get('title', 'Untitled Diagram'),
                    "type": diag.get('type', 'flowchart'),
                    "description": diag.get('description', ''),
                    "mermaid_code": diag.get('mermaid_code', '')
                })
        return diagrams