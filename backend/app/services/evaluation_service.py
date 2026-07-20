# app/services/evaluation_service.py
from typing import Dict, Any, List
# Importation unifiée des schémas de production
from app.schemas.parsing_agent_schema import ParsingAgentOutput
from app.schemas.summary_agent_schema import SummaryOutputModel
from app.schemas.glossary_agent_schema import GlossaryOutputModel
class ParsingEvaluatorService:
    """
    Service autonome d'évaluation et de calcul de métriques de fiabilité (QA)
    et de pilotage (Gestion de Projet) pour les documents techniques de Spec Kit.
    Analyse structurelle avancée basée sur la topologie du graphe et la traçabilité macro/micro.
    """

    @classmethod
    def evaluate(cls, parsed_data: ParsingAgentOutput, template_config: Dict[str, Any]) -> Dict[str, Any]:
        doc_type = parsed_data.doc_type.value

        # 1. Calcul des métriques de fiabilité technique et topologique (QA)
        technical_metrics = cls._calculate_technical_metrics(parsed_data, template_config, doc_type)

        # 2. Calcul des KPI de gestion de projet et maturité (Management)
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
        """
        Évalue la fidélité, la conformité sémantique au gabarit et l'intégrité relationnelle 
        du graphe d'éléments extrait par le LLM (anti-hallucination topologique).
        """
        filler_words = ["tbd", "n/a", "none", "not specified", "todo", "a definir", "manquant"]
        semantic_voids = 0
        truncations = 0
        quality_alerts = []

        # 1. Analyse macro-structurelle et détection de bruit textuel
        for section in parsed_data.sections:
            content_clean = section.raw_content.lower().strip()
            if any(filler == content_clean or f"[{filler}]" in content_clean for filler in filler_words):
                semantic_voids += 1
            if "..." in section.raw_content or "etc." in section.raw_content.lower():
                truncations += 1

        # Score d'adhérence au schéma basé sur la propreté du contenu
        sar_score = max(0.0, 100.0 - (semantic_voids * 20.0) - (truncations * 10.0))

        # 2. RAPPEL D'INTÉGRITÉ STRUCTURELLE (SIR) - Couverture des sections requises
        required_sections = template_config.get(doc_type, {}).get("required_sections", [])
        required_names = {sec["name"].lower().strip() for sec in required_sections}
        mapped_fields = {s.mapped_to_template_field.lower().strip() for s in parsed_data.sections if s.mapped_to_template_field}
        
        if required_names:
            missing_sections = required_names.difference(mapped_fields)
            sir_score = ((len(required_names) - len(missing_sections)) / len(required_names)) * 100.0
            for missing in missing_sections:
                quality_alerts.append(f"Section requise absente des correspondances : {missing}")
        else:
            sir_score = 100.0

        # 3. INTÉGRITÉ RELATIONNELLE DU GRAPHE (GRI) - Validation des arcs (Cibles existantes)
        elements = parsed_data.elements
        relationships = parsed_data.relationships
        
        if not relationships:
            gri_score = 100.0
        else:
            # Dictionnaire des nœuds valides indexés par identifiant et ancre de contenu court
            valid_nodes = set()
            for el in elements:
                if el.identifier:
                    valid_nodes.add(str(el.identifier).lower().strip())
                if el.content:
                    valid_nodes.add(el.content[:30].lower().strip())

            valid_relations = 0
            for rel in relationships:
                src = str(rel.source).lower().strip()
                tgt = str(rel.to).lower().strip()
                
                src_valid = any(src in node or node in src for node in valid_nodes)
                tgt_valid = any(tgt in node or node in tgt for node in valid_nodes)
                
                if src_valid and tgt_valid:
                    valid_relations += 1
                else:
                    quality_alerts.append(f"Relation orpheline détectée : Lien brisé entre '{rel.source}' et '{rel.to}'")
            
            gri_score = (valid_relations / len(relationships)) * 100.0

        # 4. INDICE DE TRAÇABILITÉ MACRO-MICRO (MMTI) - Ancrage des éléments dans les sections physiques
        if not elements:
            mmti_score = 100.0
        else:
            valid_section_titles = {s.title.lower().strip() for s in parsed_data.sections}
            linked_elements = 0
            
            for el in elements:
                if el.source_section and el.source_section.lower().strip() in valid_section_titles:
                    linked_elements += 1
                else:
                    quality_alerts.append(f"Défaut d'ancrage : L'élément '{el.identifier or el.content[:20]}' pointe vers une section introuvable")
            
            mmti_score = (linked_elements / len(elements)) * 100.0

        # 5. CONFORMITÉ DU TYPAGE DU GABARIT (MTC) - Respect de la liste restrictive attendue
        expected_element_types = {t.lower().strip() for t in template_config.get(doc_type, {}).get("expected_element_types", [])}
        if not elements or not expected_element_types:
            mtc_score = 100.0
        else:
            correct_types = sum(1 for el in elements if el.type.lower().strip() in expected_element_types)
            mtc_score = (correct_types / len(elements)) * 100.0
            
        # Détection de léthargie ou absence complète d'extraction technique
        if len(elements) == 0 and len(parsed_data.sections) > 0:
            quality_alerts.append("Extraction stérile : Aucun élément micro-technique (nœud) n'a pu être extrait")

        return {
            "schema_adherence_rate": round(sar_score, 1),
            "structural_integrity_recall": round(sir_score, 1),
            "graph_relational_integrity": round(gri_score, 1),
            "macro_micro_traceability_index": round(mmti_score, 1),
            "model_template_conformity": round(mtc_score, 1),
            "quality_alerts": quality_alerts
        }

    @staticmethod
    def _calculate_management_kpis(
        parsed_data: ParsingAgentOutput, 
        template_config: Dict[str, Any], 
        doc_type: str
    ) -> Dict[str, Any]:
        """
        Analyse l'état de préparation opérationnelle (Readiness) du document sur la base 
        des Gaps structurels et des zones d'ombre extraites.
        """
        gaps = parsed_data.structural_gaps
        open_questions = parsed_data.open_questions
        sections = parsed_data.sections

        required_sections = template_config.get(doc_type, {}).get("required_sections", [])
        required_names = {sec["name"].lower().strip() for sec in required_sections}
        mapped_fields = {s.mapped_to_template_field.lower().strip() for s in sections if s.mapped_to_template_field}

        # Taux de complétude brute par rapport aux exigences du template
        completeness_score = (
            round((len(mapped_fields.intersection(required_names)) / len(required_names)) * 100, 1)
            if required_names else 100.0
        )

        high_gaps = sum(1 for g in gaps if g.priority.upper() in ["HAUTE", "HIGH"])
        medium_gaps = sum(1 for g in gaps if g.priority.upper() in ["MOYENNE", "MEDIUM"])
        low_gaps = sum(1 for g in gaps if g.priority.upper() in ["BASSE", "LOW"])

        # Calcul pondéré de l'indice de santé
        health_index = 100.0
        health_index -= (high_gaps * 15.0)
        health_index -= (medium_gaps * 5.0)
        health_index -= (len(open_questions) * 8.0)
        
        # Pénalité de léthargie du LLM : si le texte est long mais qu'il n'a levé aucun risque/gap
        total_words = sum(len(s.raw_content.split()) for s in sections)
        if total_words > 400 and len(gaps) == 0 and len(open_questions) == 0:
            health_index -= 25.0

        health_index = max(0.0, round(health_index, 1))

        # Décision de passage de jalon (Readiness Status)
        if health_index >= 85 and high_gaps == 0 and len(open_questions) <= 2:
            readiness_status = "READY_FOR_EXECUTION"
        elif health_index >= 55:
            readiness_status = "NEEDS_REFINEMENT"
        else:
            readiness_status = "BLOCKED"

        return {
            "health_index": health_index,
            "completeness_score": completeness_score,
            "readiness_status": readiness_status,
            "extracted_metrics_summary": {
                "total_nodes_extracted": len(parsed_data.elements),
                "total_edges_extracted": len(parsed_data.relationships)
            },
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
    Version durcie et corrigée des faux négatifs sémantiques.
    """

    @classmethod
    def evaluate(cls, summary_data: SummaryOutputModel, parsed_data: ParsingAgentOutput) -> Dict[str, Any]:
        technical_metrics = cls._calculate_technical_metrics(summary_data, parsed_data)
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
        # --- 1. MATURITY ALIGNMENT SCORE (MAS) ---
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

        # --- 2. VERROU ANTI-HALLUCINATION CORRIGÉ (Token-based & Allowlist) ---
        full_parsed_text = " ".join([s.raw_content.lower() for s in parsed_data.sections])
        hallucinated_entities = 0
        
        # Dictionnaire d'implications sémantiques légitimes (Stack Web de base pour LocalStorage/WCAG)
        web_base_tokens = ["html5", "html", "css3", "css", "javascript", "js", "typescript", "api"]
        is_web_project = "localstorage" in full_parsed_text or "wcag" in full_parsed_text

        all_extracted_tech = (
            summary_data.technical_stack.languages_and_frameworks +
            summary_data.technical_stack.architectural_constraints +
            summary_data.critical_dependencies
        )

        for item in all_extracted_tech:
            item_clean = item.lower().strip()
            
            # Découpage de l'exigence en mots significatifs (longueur > 3)
            item_replaced = item_clean.replace("/", " ")
            words = [w.strip(",.()\"'") for w in item_replaced.split() if len(w.strip(",.()\"'")) > 3]
            
            # Une entité est validée si au moins un de ses mots clés significatifs est dans le texte source
            # OU s'il s'agit d'une déduction de langage Web légitime pour un projet local-first
            match_found = any(word in full_parsed_text for word in words)
            if not match_found and is_web_project:
                match_found = any(word in web_base_tokens for word in words)
                
            if not match_found and words:  # Si aucun mot clé n'est ancré ou déduit
                hallucinated_entities += 1

        # --- 3. EXTRACTION COMPLETENESS RATE (ECR) GRANULAIRE ---
        lang_count = len(summary_data.technical_stack.languages_and_frameworks)
        const_count = len(summary_data.technical_stack.architectural_constraints)
        dep_count = len(summary_data.critical_dependencies)

        ecr_score = 0.0
        if lang_count >= 2: ecr_score += 35.0
        elif lang_count == 1: ecr_score += 15.0

        if const_count >= 2: ecr_score += 35.0
        elif const_count == 1: ecr_score += 15.0

        if dep_count >= 1: ecr_score += 30.0

        # Application des pénalités d'hallucination réelles
        final_mas = max(0.0, mas_score - (hallucinated_entities * 20.0))
        final_ecr = max(0.0, ecr_score - (hallucinated_entities * 15.0))

        # --- 4. CONCISENESS & PRECISION SCORE (CPS) ---
        word_count = len(summary_data.executive_brief.split())
        if word_count == 0:
            cps_score = 0.0
        elif 30 <= word_count <= 150:
            cps_score = 100.0  
        elif word_count < 30:
            cps_score = 60.0   
        else:
            cps_score = 70.0   

        return {
            "maturity_alignment_score": round(final_mas, 1),
            "conciseness_precision_score": cps_score,
            "extraction_completeness_rate": round(final_ecr, 1),
            "brief_word_count": word_count,
            "hallucinations_detected_count": hallucinated_entities
        }

    @staticmethod
    def _calculate_management_kpis(summary_data: SummaryOutputModel) -> Dict[str, Any]:
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
class GlossaryEvaluatorService:
    """
    Service autonome d'évaluation pour le Glossary Agent.
    Intègre les métriques globales d'ancrage géométrique et anti-tautologie.
    """

    @classmethod
    def evaluate(cls, glossary_data: GlossaryOutputModel, parsed_data: ParsingAgentOutput, candidate_terms: List[str]) -> Dict[str, Any]:
        technical_metrics = cls._calculate_technical_metrics(glossary_data, parsed_data, candidate_terms)
        management_kpis = cls._calculate_management_kpis(glossary_data)

        tcr = technical_metrics["term_coverage_rate"]
        car = technical_metrics["categorization_accuracy_rate"]
        dps = technical_metrics["definition_precision_score"]
        ata = technical_metrics["anti_tautology_adherence"]
        cap = technical_metrics["contextual_anchor_precision"]

        # Arbitrage strict intégrant les nouvelles métriques d'ancrage topologique
        if tcr >= 90.0 and car == 100.0 and dps >= 90.0 and ata >= 90.0 and cap >= 90.0:
            semantic_status = "READY_FOR_ANCHORING"
        elif tcr >= 70.0 and car >= 70.0 and dps >= 60.0 and ata >= 70.0 and cap >= 70.0:
            semantic_status = "NEEDS_REFINEMENT"
        else:
            semantic_status = "BLOCKED"

        return {
            "agent_evaluated": "Glossary Agent",
            "project_name": glossary_data.project_name if glossary_data.project_name else parsed_data.project_info.get("project_name", "Inconnu"),
            "semantic_anchoring_status": semantic_status,
            "technical_evaluation": technical_metrics,
            "project_management_kpis": management_kpis
        }

    @staticmethod
    def _calculate_technical_metrics(
        glossary_data: GlossaryOutputModel, 
        parsed_data: ParsingAgentOutput, 
        candidate_terms: List[str]
    ) -> Dict[str, Any]:
        from app.core.metrics import calculate_ata, calculate_cap

        # Sérialisation propre des modèles Pydantic pour conformité avec le module metrics core
        items_dict = [item.model_dump() if hasattr(item, "model_dump") else item for item in glossary_data.items]
        elements_dict = [el.model_dump() if hasattr(el, "model_dump") else el for el in parsed_data.elements]
        sections_dict = [sec.model_dump() if hasattr(sec, "model_dump") else sec for sec in parsed_data.sections]

        # Appel direct aux métriques centralisées de metrics.py
        ata_score = calculate_ata(items_dict)
        cap_score = calculate_cap(items_dict, elements_dict, sections_dict)

        generated_terms = {item.term.lower().strip() for item in glossary_data.items}
        
        if not candidate_terms:
            tcr_score = 100.0
        else:
            matched_terms = sum(1 for term in candidate_terms if term.lower().strip() in generated_terms)
            tcr_score = (matched_terms / len(candidate_terms)) * 100.0

        tech_indicators = [
            "jwt", "api", "sdk", "localstorage", "postgres", "fastapi", "http", 
            "json", "orm", "alembic", "css", "ui", "rsc", "next.js", "tailwind", 
            "node", "jest", "ci", "cd", "branching", "workflow", "repo"
        ]
        metadata_indicators = ["version", "ratified", "amended", "amendment", "section", "identifier", "created", "status"]
        
        classification_errors = 0
        for item in glossary_data.items:
            cat_value = item.category.value if hasattr(item.category, "value") else str(item.category)
            term_clean = item.term.lower().strip()
            
            if cat_value == "BUSINESS_DOMAIN":
                if any(indicator in term_clean for indicator in tech_indicators):
                    classification_errors += 1
                elif any(meta in term_clean for meta in metadata_indicators):
                    classification_errors += 1
                    
        car_score = 100.0 - (classification_errors * 15.0) if glossary_data.items else 100.0
        car_score = max(0.0, car_score)

        structural_noise_count = 0
        case_duplicates = 0
        structural_noise_blacklist = ["ii", "iii", "iv", "v", "vi", "vii", "non", "tbd"]
        
        seen_terms = set()
        french_drift_detected = False
        french_words = [" est ", " pour ", " avec ", " dans ", " les ", " conçu ", " obligatoire "]
        
        for item in glossary_data.items:
            term_clean = item.term.lower().strip()
            
            if term_clean in seen_terms:
                case_duplicates += 1
            seen_terms.add(term_clean)
            
            if term_clean in structural_noise_blacklist:
                structural_noise_count += 1
            
            if any(word in item.project_definition.lower() for word in french_words):
                french_drift_detected = True

        # Calcul sémantique affiné combinant la précision locale et globale
        dps_score = 100.0
        dps_score -= (case_duplicates * 15.0)
        dps_score -= (structural_noise_count * 20.0)
        
        if french_drift_detected:
            dps_score -= 40.0
            
        dps_score = max(0.0, dps_score)

        return {
            "term_coverage_rate": round(tcr_score, 1),
            "categorization_accuracy_rate": round(car_score, 1),
            "definition_precision_score": round(dps_score, 1),
            "anti_tautology_adherence": round(ata_score, 1),
            "contextual_anchor_precision": round(cap_score, 1),
            "structural_noise_count": structural_noise_count,
            "case_duplicates_count": case_duplicates,
            "classification_errors_count": classification_errors,
            "language_drift_detected": french_drift_detected
        }

    @staticmethod
    def _calculate_management_kpis(glossary_data: GlossaryOutputModel) -> Dict[str, Any]:
        total_items = len(glossary_data.items)
        business_count = 0
        tech_count = 0
        explicit_count = 0
        implicit_count = 0

        for item in glossary_data.items:
            cat_value = item.category.value if hasattr(item.category, "value") else str(item.category)
            disc_value = item.discovery.value if hasattr(item.discovery, "value") else str(item.discovery)

            if cat_value == "BUSINESS_DOMAIN":
                business_count += 1
            elif cat_value == "TECHNICAL_STACK":
                tech_count += 1

            if disc_value == "EXPLICIT":
                explicit_count += 1
            elif disc_value == "IMPLICIT":
                implicit_count += 1

        return {
            "total_extracted_terms": total_items,
            "business_domain_terms_count": business_count,
            "technical_stack_terms_count": tech_count,
            "explicit_terms_count": explicit_count,
            "implicit_terms_inferred_count": implicit_count
        }
# class GlossaryEvaluatorService:
#     """
#     Service autonome d'évaluation pour le Glossary Agent.
#     """

#     @classmethod
#     def evaluate(cls, glossary_data: Any, parsed_data: Any, candidate_terms: List[str]) -> Dict[str, Any]:
#         technical_metrics = cls._calculate_technical_metrics(glossary_data, candidate_terms)
#         management_kpis = cls._calculate_management_kpis(glossary_data)

#         tcr = technical_metrics["term_coverage_rate"]
#         car = technical_metrics["categorization_accuracy_rate"]
#         dps = technical_metrics["definition_precision_score"]

#         if tcr >= 90.0 and car == 100.0 and dps >= 90.0:
#             semantic_status = "READY_FOR_ANCHORING"
#         elif tcr >= 70.0 and car >= 70.0 and dps >= 60.0:
#             semantic_status = "NEEDS_REFINEMENT"
#         else:
#             semantic_status = "BLOCKED"

#         return {
#             "agent_evaluated": "Glossary Agent",
#             "project_name": glossary_data.project_name if glossary_data.project_name else parsed_data.project_info.get("project_name", "Inconnu"),
#             "semantic_anchoring_status": semantic_status,
#             "technical_evaluation": technical_metrics,
#             "project_management_kpis": management_kpis
#         }

#     @staticmethod
#     def _calculate_technical_metrics(glossary_data: Any, candidate_terms: List[str]) -> Dict[str, Any]:
#         generated_terms = {item.term.lower().strip() for item in glossary_data.items}
        
#         if not candidate_terms:
#             tcr_score = 100.0
#         else:
#             matched_terms = sum(1 for term in candidate_terms if term.lower().strip() in generated_terms)
#             tcr_score = (matched_terms / len(candidate_terms)) * 100.0

#         tech_indicators = [
#             "jwt", "api", "sdk", "localstorage", "postgres", "fastapi", "http", 
#             "json", "orm", "alembic", "css", "ui", "rsc", "next.js", "tailwind", 
#             "node", "jest", "ci", "cd", "branching", "workflow", "repo"
#         ]
        
#         metadata_indicators = ["version", "ratified", "amended", "amendment", "section", "identifier", "created", "status"]
        
#         classification_errors = 0
#         for item in glossary_data.items:
#             cat_value = item.category.value if hasattr(item.category, "value") else str(item.category)
#             term_clean = item.term.lower().strip()
            
#             if cat_value == "BUSINESS_DOMAIN":
#                 if any(indicator in term_clean for indicator in tech_indicators):
#                     classification_errors += 1
#                 elif any(meta in term_clean for meta in metadata_indicators):
#                     classification_errors += 1
                    
#         car_score = 100.0 - (classification_errors * 15.0) if glossary_data.items else 100.0
#         car_score = max(0.0, car_score)

#         tautology_violations = 0
#         structural_noise_count = 0
#         case_duplicates = 0
#         structural_noise_blacklist = ["ii", "iii", "iv", "v", "vi", "vii", "non", "tbd"]
        
#         seen_terms = set()
#         french_drift_detected = False
#         french_words = [" est ", " pour ", " avec ", " dans ", " les ", " conçu ", " obligatoire "]
        
#         for item in glossary_data.items:
#             term_clean = item.term.lower().strip()
            
#             if term_clean in seen_terms:
#                 case_duplicates += 1
#             seen_terms.add(term_clean)
            
#             if term_clean in structural_noise_blacklist:
#                 structural_noise_count += 1
                
#             if term_clean in item.project_definition.lower():
#                 tautology_violations += 1
            
#             if any(word in item.project_definition.lower() for word in french_words):
#                 french_drift_detected = True

#         dps_score = 100.0
#         dps_score -= (tautology_violations * 20.0)
#         dps_score -= (case_duplicates * 15.0)
#         dps_score -= (structural_noise_count * 20.0)
        
#         if french_drift_detected:
#             dps_score -= 40.0
            
#         dps_score = max(0.0, dps_score)

#         return {
#             "term_coverage_rate": round(tcr_score, 1),
#             "categorization_accuracy_rate": round(car_score, 1),
#             "definition_precision_score": round(dps_score, 1),
#             "tautology_violations_count": tautology_violations,
#             "structural_noise_count": structural_noise_count,
#             "case_duplicates_count": case_duplicates,
#             "classification_errors_count": classification_errors,
#             "language_drift_detected": french_drift_detected
#         }

#     @staticmethod
#     def _calculate_management_kpis(glossary_data: Any) -> Dict[str, Any]:
#         total_items = len(glossary_data.items)
#         business_count = 0
#         tech_count = 0
#         explicit_count = 0
#         implicit_count = 0

#         for item in glossary_data.items:
#             cat_value = item.category.value if hasattr(item.category, "value") else str(item.category)
#             disc_value = item.discovery.value if hasattr(item.discovery, "value") else str(item.discovery)

#             if cat_value == "BUSINESS_DOMAIN":
#                 business_count += 1
#             elif cat_value == "TECHNICAL_STACK":
#                 tech_count += 1

#             if disc_value == "EXPLICIT":
#                 explicit_count += 1
#             elif disc_value == "IMPLICIT":
#                 implicit_count += 1

#         return {
#             "total_extracted_terms": total_items,
#             "business_domain_terms_count": business_count,
#             "technical_stack_terms_count": tech_count,
#             "explicit_terms_count": explicit_count,
#             "implicit_terms_inferred_count": implicit_count
#         }
