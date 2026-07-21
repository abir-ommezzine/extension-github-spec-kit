# app/utils/glossary_tools.py
import os
import re
import json
from typing import Dict, Any, List, Set

class GlossaryHarvesterService:
    ARCHITECTURAL_SIGNALS = {
        "jwt", "rbac", "abac", "cors", "rest", "graphql", "crud", "spa", "ssr", "rsc",
        "api", "sdk", "orm", "uuid", "ci/cd", "json", "localstorage", "sessionstorage",
        "db", "sql", "nosql", "middleware", "webhook", "tls", "ssl", "oauth", "oidc"
    }

    IMPLICIT_MAPPING = {
        r"\b(date|time|timestamp|created_at|updated_at)\b": "ISO 8601",
        r"\b(password|hash|salt|bcrypt|argon2)\b": "Cryptographic Hashing",
        r"\b(currency|amount|price|decimal|monetary)\b": "Fixed-Point Numeric Constraint",
        r"\b(role|permission|admin|instructor|student|owner)\b": "Role-Based Access Control (RBAC)",
        r"\b(origin|cross-origin|domain|header)\b": "CORS Standard"
    }

    @classmethod
    def generate_and_cache_anchors(cls, parsed_data: Dict[str, Any]) -> List[str]:
        """
        Extrait les identifiants physiques du graphe et génère un fichier de cache 
        sous backend/ressources/ pour guider géométriquement l'agent LLM.
        """
        elements = parsed_data.get("elements", [])
        sections = parsed_data.get("sections", [])
        valid_anchors: Set[str] = set()

        for el in elements:
            ident = el.get("identifier", "").strip()
            if ident:
                valid_anchors.add(ident)

        for sec in sections:
            title = sec.get("title", "").strip()
            if title:
                valid_anchors.add(title)

        # Règle d'exclusion des ancres invalides ou trop génériques
        filtered_anchors = [
            a for a in valid_anchors 
            if (a.startswith("T") and a[1:].isdigit()) 
            or ("-" in a) 
            or a.isupper() 
            or len(a.split()) > 1
        ]

        # Détermination du chemin du dossier ressources
        base_dir = "backend" if os.path.exists("backend") else "."
        cache_dir = os.path.join(base_dir, "ressources")
        os.makedirs(cache_dir, exist_ok=True)
        
        cache_path = os.path.join(cache_dir, "topological_anchors_cache.json")
        
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(sorted(filtered_anchors), f, indent=2, ensure_ascii=False)
            
        return filtered_anchors

    @classmethod
    def harvest_candidates(cls, parsed_data: Dict[str, Any]) -> List[str]:
        """
        Moissonneur universel déterministe invariant. Élimine le bruit logique, 
        termes Agile/process, fuites de nom de projet et fragments de standards.
        """
        candidates: Set[str] = set()
        sections = parsed_data.get("sections", [])
        elements = parsed_data.get("elements", [])

        project_name = parsed_data.get("project_info", {}).get("project_name", "").strip()
        
        # Collecte des identifiants explicites déclarés dans les nœuds
        explicit_identifiers = set()
        for el in elements:
            identifier = el.get("identifier", "")
            content = el.get("content", "")
            if identifier:
                clean_id = identifier.strip()
                explicit_identifiers.add(clean_id)
                if not ("-" in clean_id or "_" in clean_id or (clean_id.startswith("T") and clean_id[1:].isdigit())):
                    candidates.add(clean_id)
            cls._extract_from_text(content, candidates)
            cls._deduce_implicit_standards(content, candidates)

        for section in sections:
            cls._extract_from_text(section.get("title", ""), candidates)
            cls._extract_from_text(section.get("raw_content", ""), candidates)
            cls._deduce_implicit_standards(section.get("raw_content", ""), candidates)

        # Normalisation initiale des espaces
        pre_clean = set()
        for term in candidates:
            clean_term = term.replace("\n", " ").strip()
            clean_term = re.sub(r'\s+\d+$', '', clean_term)
            if len(clean_term) >= 2 and not clean_term.isdigit():
                pre_clean.add(clean_term)

        # 1. MATRICE ENRICHIE D'EXCLUSION : Verbes HTTP, Bruit Agile, Mots génériques
        EXCLUSION_MATRIX = {
            # Network plumbing, Verbes & Headers HTTP
            "get", "post", "put", "delete", "patch", "options", "head", "http", "https", 
            "url", "uri", "base url", "content-type", "authorization header", "response envelope",
            "application/json", "mime", "host", "port", "endpoint", "endpoints", "route", "routes",
            
            # Vocabulaire d'anglais générique et conteneurs
            "input", "output", "data", "file", "system", "value", "field", "type", "description",
            
            # Processus Agile, Git & Méthodologie de Build (Nouveaux filtres)
            "acceptance scenarios", "independent test", "feature branch", "user story", "story",
            "given", "when", "then", "and", "but", "between", "reaches", "at least", 
            "greater", "less", "equals", "must", "should", "contains",
            
            # Métadonnées documentaires & Gouvernance
            "purpose", "needs", "status", "created", "ratified", "amended", "governance", "iso",
            "last amended", "stack", "core", "auth", "test", "app", "main", "total", "ok", "true", "false", 
            "project", "version", "step", "checklist", "priority",
            
            # Types d'exécution locale et variables
            "limit", "skip", "page", "offset", "client", "async_session", "session", "fixture",
            "emailstr", "str", "int", "float", "bool", "dict", "list", "set", "tuple", "jsonresponse"
        }
        
        DOCUMENT_ABBREVIATIONS = {"fr", "sc", "us", "con", "asm", "ii", "iii", "iv", "v", "vi"}
        ROMAN_NUMERALS_REGEX = re.compile(r'^[IVXLC]+$', re.IGNORECASE)

        normalized_map = {}
        for term in pre_clean:
            term_lower = term.lower()
            words = term.split()

            # 2. FILTRE CONTRE LES CHIFFRES ROMAINS (II, III) ET ABRÉVIATIONS DE SECTIONS
            if ROMAN_NUMERALS_REGEX.match(term) or term_lower in DOCUMENT_ABBREVIATIONS:
                continue

            # 3. RÈGLE D'INVARIANT SYNTAXIQUE CONTRE LES FUITES GRAMMATICALES
            if len(words) == 1 and term.islower():
                if term not in explicit_identifiers and term_lower not in cls.ARCHITECTURAL_SIGNALS:
                    continue

            # 4. FILTRE AMÉLIORÉ DU NOM DE PROJET (Exclut "CourseHub" si le projet est "CourseHub API")
            if project_name:
                p_clean = project_name.lower().replace(" api", "").strip()
                if term_lower == p_clean or term_lower == project_name.lower() or term_lower == f"{p_clean} api":
                    continue

            if term.startswith("/") or "\\" in term or any(term_lower.endswith(ext) for ext in [".py", ".md", ".json", ".yaml"]):
                continue

            if term_lower.startswith("phase") or "phase" in term_lower.split() or term_lower.startswith("task"):
                continue

            if ("-" in term or "_" in term) and term.isupper():
                continue

            if any(char in term for char in ["(", ")", "[", "]", "{", "}", "...", "=", ":"]):
                continue

            if term_lower in EXCLUSION_MATRIX:
                continue

            # Élimination des exemples alphanumériques (ex: pass123)
            if any(c.isdigit() for c in term) and not any(tech in term_lower for tech in ["python", "postgresql", "sqlalchemy", "16", "3.12", "2.0", "8601"]):
                continue

            if term_lower in normalized_map:
                if term.isupper() and not normalized_map[term_lower].isupper():
                    normalized_map[term_lower] = term
            else:
                normalized_map[term_lower] = term

        return sorted(list(set(normalized_map.values())))

    @classmethod
    def _extract_from_text(cls, text: str, candidate_set: Set[str]) -> None:
        if not text:
            return
        acronyms = re.findall(r"\b[A-Z]{2,6}\b", text)
        for acro in acronyms:
            candidate_set.add(acro)

        camel_cases = re.findall(r"\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b", text)
        for camel in camel_cases:
            candidate_set.add(camel)

        # 5. REGEX AMÉLIORÉE POUR CAPTURER LES STANDARDS COMPLETS (ex: ISO 8601 sans troncature)
        tech_versions = re.findall(r"\b(?:ISO|RFC|[A-Za-z]{3,})(?:[\s\-]?\d+)+(?:\.\d+)*\+?\b", text, re.IGNORECASE)
        for tech in tech_versions:
            clean_tech = tech.strip()
            if clean_tech.lower().startswith("iso"):
                clean_tech = re.sub(r"^iso", "ISO", clean_tech, flags=re.IGNORECASE)
            candidate_set.add(clean_tech)

        inline_highlights = re.findall(r"`([^`]+)`|\*\*([^*]+)\*\*", text)
        for match in inline_highlights:
            highlighted = match[0] if match[0] else match[1]
            if highlighted and len(highlighted.strip().split()) <= 2:
                if not (highlighted.endswith(".py") or "/" in highlighted):
                    candidate_set.add(highlighted.strip())

        words = re.findall(r"\b[a-zA-Z\-]+\b", text.lower())
        for word in words:
            if word in cls.ARCHITECTURAL_SIGNALS:
                if word in ["jwt", "rbac", "abac", "cors", "crud", "spa", "ssr", "rsc", "api", "sdk", "orm", "uuid", "json", "tls", "ssl", "oauth", "oidc"]:
                    candidate_set.add(word.upper())
                elif word == "localstorage":
                    candidate_set.add("LocalStorage")
                elif word == "sessionstorage":
                    candidate_set.add("SessionStorage")
                else:
                    candidate_set.add(word.capitalize())

    @classmethod
    def _deduce_implicit_standards(cls, text: str, candidate_set: Set[str]) -> None:
        if not text:
            return
        text_lower = text.lower()
        for regex, implicit_term in cls.IMPLICIT_MAPPING.items():
            if re.search(regex, text_lower):
                candidate_set.add(implicit_term)



