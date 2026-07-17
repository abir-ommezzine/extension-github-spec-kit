# app/services/evaluation_service.py
from typing import Dict, Any, List
# Importation unifiée du schéma de production
from app.schemas.parsing_agent_schema import ParsingAgentOutput
from app.schemas.summary_agent_schema import SummaryOutputModel


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
        summary_data: SummaryOutputModel, 
        parsed_data: ParsingAgentOutput
    ) -> Dict[str, Any]:
        """
        Calcule les scores d'alignement logique, de concision et applique des pénalités de qualité.
        """
        # [Garder le bloc existant du calcul initial de real_status et narrative_assessment...]
        from app.services.evaluation_service import ParsingEvaluatorService
        parser_kpis = ParsingEvaluatorService._calculate_management_kpis(parsed_data, {}, parsed_data.doc_type.value)
        real_status = parser_kpis.get("readiness_status", "BLOCKED")
        narrative_assessment = summary_data.maturity_assessment.upper()
        
        alignment_success = False
        if real_status == "READY_FOR_EXECUTION" and ("PRÊT" in narrative_assessment or "READY" in narrative_assessment):
            alignment_success = True
        elif real_status == "NEEDS_REFINEMENT" and ("IMMATURE" in narrative_assessment or "REFINEMENT" in narrative_assessment or "PRÊT" in narrative_assessment):
            alignment_success = True
        elif real_status == "BLOCKED" and ("CRITIQUE" in narrative_assessment or "BLOCKED" in narrative_assessment):
            alignment_success = True

        mas_score = 100.0 if alignment_success else 40.0

        # --- NOUVEAU : SÉCURITÉ ANTI-PARROTAGE (Anti-Echoing Rule) ---
        # Si le LLM recopie les chaînes brutes injectées au lieu d'utiliser ses propres mots, on le sanctionne.
        narrative_raw = summary_data.maturity_assessment
        forbidden_echoes = ["READY_FOR_EXECUTION", "NEEDS_REFINEMENT", "score de complétude", "health_index"]
        echo_penalty = 0.0
        for echo in forbidden_echoes:
            if echo in narrative_raw:
                echo_penalty += 25.0
        
        mas_score = max(0.0, mas_score - echo_penalty)

        # --- NOUVEAU : DÉTECTION DE LA DÉRIVE LINGUISTIQUE (Language Guard) ---
        # Si des mots de liaison français courants apparaissent dans un brief qui doit être en anglais technique
        brief_raw = summary_data.executive_brief.lower()
        french_words = [" est ", " pour ", " avec ", " dans ", " les ", " conçu "]
        language_penalty = 0.0
        if any(word in brief_raw for word in french_words):
            language_penalty = 40.0  # Lourde sanction pour forcer l'anglais technique

        # --- CALCUL CONCISENESS (CPS) ---
        word_count = len(summary_data.executive_brief.split())
        if word_count == 0:
            cps_score = 0.0
        elif 30 <= word_count <= 150:
            cps_score = max(0.0, 100.0 - language_penalty) # Applique la pénalité de langue ici
        elif word_count < 30:
            cps_score = max(0.0, 60.0 - language_penalty)
        else:
            cps_score = max(0.0, 70.0 - language_penalty)

        # --- COMPLÉTUDE (ECR) ---
        filled_lists = 0
        if len(summary_data.technical_stack.languages_and_frameworks) > 0:
            filled_lists += 1
        if len(summary_data.technical_stack.architectural_constraints) > 0:
            filled_lists += 1
        if len(summary_data.critical_dependencies) > 0:
            filled_lists += 1
            
        ecr_score = (filled_lists / 3) * 100.0

        return {
            "maturity_alignment_score": mas_score,
            "conciseness_precision_score": cps_score,
            "extraction_completeness_rate": ecr_score,
            "brief_word_count": word_count,
            "echo_penalty_applied": echo_penalty > 0,
            "language_drift_detected": language_penalty > 0
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
class SummaryEvaluatorService:
    """
    Service autonome d'évaluation pour le Summary Agent.
    Mesure la concision, la complétude de l'extraction de la stack technique, 
    et la cohérence logique du diagnostic par rapport au Parser.
    """

    @classmethod
    def evaluate(cls, summary_data: SummaryOutputModel, parsed_data: ParsingAgentOutput) -> Dict[str, Any]:
        """
        Orchestre l'évaluation de la synthèse en croisant le modèle validé 
        et les données initiales du parser.
        """
        # 1. Calcul des métriques de fiabilité technique (QA)
        technical_metrics = cls._calculate_technical_metrics(summary_data, parsed_data)

        # 2. Calcul des KPI de gestion de projet (Management)
        management_kpis = cls._calculate_management_kpis(summary_data)

        return {
            "agent_evaluated": "Summary Agent",
            "project_name": parsed_data.project_info.get("project_name", "Inconnu"),
            "technical_evaluation": technical_metrics,
            "project_management_kpis": management_kpis
        }

    @staticmethod
    def _calculate_technical_metrics(
        summary_data: SummaryOutputModel, 
        parsed_data: ParsingAgentOutput
    ) -> Dict[str, Any]:
        """
        Calcule les scores d'alignement logique et de concision.
        """
        # --- 1. MATURITY ALIGNMENT SCORE (MAS) ---
        from app.services.evaluation_service import ParsingEvaluatorService
        parser_kpis = ParsingEvaluatorService._calculate_management_kpis(parsed_data, {}, parsed_data.doc_type.value)
        real_status = parser_kpis.get("readiness_status", "BLOCKED")
        
        narrative_assessment = summary_data.maturity_assessment.upper()
        
        # Règle d'alignement croisé
        alignment_success = False
        if real_status == "READY_FOR_EXECUTION" and ("PRÊT" in narrative_assessment or "READY" in narrative_assessment):
            alignment_success = True
        elif real_status == "NEEDS_REFINEMENT" and ("IMMATURE" in narrative_assessment or "REFINEMENT" in narrative_assessment or "PRÊT" in narrative_assessment):
            alignment_success = True
        elif real_status == "BLOCKED" and ("CRITIQUE" in narrative_assessment or "BLOCKED" in narrative_assessment):
            alignment_success = True

        mas_score = 100.0 if alignment_success else 40.0

        # --- 2. CONCISENESS & PRECISION SCORE (CPS) ---
        word_count = len(summary_data.executive_brief.split())
        if word_count == 0:
            cps_score = 0.0
        elif 30 <= word_count <= 150:
            cps_score = 100.0  
        elif word_count < 30:
            cps_score = 60.0   
        else:
            cps_score = 70.0   

        # --- 3. EXTRACTION COMPLETENESS RATE (ECR) ---
        filled_lists = 0
        if len(summary_data.technical_stack.languages_and_frameworks) > 0:
            filled_lists += 1
        if len(summary_data.technical_stack.architectural_constraints) > 0:
            filled_lists += 1
        if len(summary_data.critical_dependencies) > 0:
            filled_lists += 1
            
        ecr_score = (filled_lists / 3) * 100.0

        return {
            "maturity_alignment_score": mas_score,
            "conciseness_precision_score": cps_score,
            "extraction_completeness_rate": ecr_score,
            "brief_word_count": word_count
        }

    @staticmethod
    def _calculate_management_kpis(summary_data: SummaryOutputModel) -> Dict[str, Any]:
        """
        Extrait les KPI de volume et de risques pour le tableau de bord du projet.
        """
        languages_count = len(summary_data.technical_stack.languages_and_frameworks)
        constraints_count = len(summary_data.technical_stack.architectural_constraints)
        dependencies_count = len(summary_data.critical_dependencies)

        if dependencies_count >= 4:
            risk_exposure = "ÉLEVÉ"
        elif 1 <= dependencies_count <= 3:
            risk_exposure = "MODÉRÉ"
        else:
            risk_exposure = "FAIBLE"

        return {
            "extracted_technologies_count": languages_count,
            "architectural_constraints_count": constraints_count,
            "external_dependencies_count": dependencies_count,
            "external_risk_exposure": risk_exposure
        }