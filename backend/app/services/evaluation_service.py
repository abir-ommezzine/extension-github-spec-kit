# app/services/evaluation_service.py
from typing import Dict, Any, List
# Importation unifiée du schéma de production
from app.schemas.parsing_agent_schema import ParsingAgentOutput


class ParsingEvaluatorService:
    """
    Service autonome d'évaluation et de calcul de métriques de fiabilité (QA)
    et de pilotage (Gestion de Projet) pour les documents techniques de Spec Kit.
    """

    @classmethod
    def evaluate(cls, parsed_data: ParsingAgentOutput, template_config: Dict[str, Any]) -> Dict[str, Any]:
        doc_type = parsed_data.doc_type.value

        # 1. Calcul des métriques de fiabilité technique (QA)
        technical_metrics = cls._calculate_technical_metrics(parsed_data, template_config, doc_type)

        # 2. Calcul des KPI de gestion de projet (Management)
        management_kpis = cls._calculate_management_kpis(parsed_data, template_config, doc_type)

        return {
            "document_type": doc_type,
            "project_name": parsed_data.project_info.get("project_name", "Inconnu"),
            "technical_evaluation": technical_metrics,
            "project_management_kpis": management_kpis
        }

    @staticmethod
    def _calculate_technical_metrics(
        parsed_data: ParsingAgentOutput, 
        template_config: Dict[str, Any], 
        doc_type: str
    ) -> Dict[str, Any]:
        sections = parsed_data.sections
        gaps = parsed_data.structural_gaps
        open_questions = parsed_data.open_questions

        mapped_fields = {s.mapped_to_template_field for s in sections if s.mapped_to_template_field}
        gap_fields = {g.missing_section for g in gaps}

        # Détection des contradictions logiques
        contradictions = mapped_fields.intersection(gap_fields)
        sar_score = max(0.0, 100.0 - (len(contradictions) * 25.0))

        # Couverture du gabarit global
        required_sections = template_config.get(doc_type, {}).get("required_sections", [])
        required_names = {sec["name"] for sec in required_sections}
        covered_fields = mapped_fields.union(gap_fields)
        sir_score = (len(required_names.intersection(covered_fields)) / len(required_names) * 100) if required_names else 100.0

        # Exactitude textuelle
        text_scores: List[float] = []
        for s in sections:
            if s.mapped_to_template_field:
                content_len = len(s.raw_content.strip()) if s.raw_content else 0
                if content_len == 0:
                    text_scores.append(0.0)
                elif content_len < 20:
                    text_scores.append(50.0)
                else:
                    text_scores.append(100.0)
        tfs_score = sum(text_scores) / len(text_scores) if text_scores else 100.0

        # Omissions de doutes (ExR)
        exr_score = 100.0
        for s in sections:
            if s.mapped_to_template_field is None and s.raw_content and "TBD" in s.raw_content:
                if len(open_questions) == 0:
                    exr_score = 50.0

        return {
            "schema_adherence_rate": sar_score,
            "structural_integrity_recall": sir_score,
            "text_fidelity_score": tfs_score,
            "extraction_recall": exr_score,
            "contradictions": list(contradictions)
        }

    @staticmethod
    def _calculate_management_kpis(
        parsed_data: ParsingAgentOutput, 
        template_config: Dict[str, Any], 
        doc_type: str
    ) -> Dict[str, Any]:
        sections = parsed_data.sections
        gaps = parsed_data.structural_gaps
        open_questions = parsed_data.open_questions

        required_sections = template_config.get(doc_type, {}).get("required_sections", [])
        required_names = {sec["name"] for sec in required_sections}
        mapped_fields = {s.mapped_to_template_field for s in sections if s.mapped_to_template_field}

        completeness_score = (
            round((len(mapped_fields.intersection(required_names)) / len(required_names)) * 100, 1)
            if required_names else 100.0
        )

        high_gaps = sum(1 for g in gaps if g.priority.upper() in ["HAUTE", "HIGH"])
        medium_gaps = sum(1 for g in gaps if g.priority.upper() in ["MOYENNE", "MEDIUM"])
        low_gaps = sum(1 for g in gaps if g.priority.upper() in ["BASSE", "LOW"])

        health_index = 100.0
        health_index -= (high_gaps * 15)
        health_index -= (medium_gaps * 5)
        health_index -= (len(open_questions) * 10)
        health_index = max(0.0, round(health_index, 1))

        if health_index >= 85 and high_gaps == 0:
            readiness_status = "READY_FOR_EXECUTION"
        elif health_index >= 60:
            readiness_status = "NEEDS_REFINEMENT"
        else:
            readiness_status = "BLOCKED"

        return {
            "health_index": health_index,
            "completeness_score": completeness_score,
            "readiness_status": readiness_status,
            "gaps_summary": {
                "high_severity": high_gaps,
                "medium_severity": medium_gaps,
                "low_severity": low_gaps,
                "unresolved_uncertainties": len(open_questions)
            }
        }