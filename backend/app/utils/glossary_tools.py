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
        Moissonneur universel déterministe invariant. Élimine le bruit logique 
        et grammatical via des règles syntaxiques agnostiques.
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

        # Matrice globale d'exclusion des bruits
        EXCLUSION_MATRIX = {
            "get", "post", "put", "delete", "patch", "options", "head", "http", "https", 
            "url", "uri", "base url", "content-type", "authorization header", "response envelope",
            "application/json", "mime", "host", "port", "endpoint", "endpoints", "route", "routes",
            "given", "when", "then", "and", "but", "between", "reaches", "at least", 
            "greater", "less", "equals", "must", "should", "contains",
            "purpose", "needs", "status", "created", "ratified", "amended", "governance", 
            "stack", "core", "auth", "test", "app", "main", "total", "ok", "true", "false", 
            "project", "version", "step", "checklist", "priority",
            "limit", "skip", "page", "offset", "client", "async_session", "session", "fixture",
            "emailstr", "str", "int", "float", "bool", "dict", "list", "set", "tuple", "jsonresponse"
        }
        
        normalized_map = {}
        for term in pre_clean:
            term_lower = term.lower()
            words = term.split()

            # 1. RÈGLE D'INVARIANT SYNTAXIQUE CONTRE LES FUITES GRAMMATICALES (ATA/TCR)
            # Un mot unique en minuscules est rejeté sauf s'il est une entité du graphe ou une stack connue
            if len(words) == 1 and term.islower():
                if term not in explicit_identifiers and term_lower not in cls.ARCHITECTURAL_SIGNALS:
                    continue

            if project_name and (term_lower == project_name.lower() or term_lower == f"{project_name.lower()} api"):
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

            # Élimination des chaînes d'exemples alphanumériques (ex: pass123)
            if any(c.isdigit() for c in term) and not any(tech in term_lower for tech in ["python", "postgresql", "sqlalchemy", "16", "3.12", "2.0"]):
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

        tech_versions = re.findall(r"\b[A-Za-z]{3,}(?:\.[A-Za-z]+)?\s?\d+(?:\.\d+)*\+?\b", text)
        for tech in tech_versions:
            candidate_set.add(tech.strip())

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
# # app/utils/glossary_tools.py
# import re
# from typing import Dict, Any, List, Set

# class GlossaryHarvesterService:
#     """
#     Outil d'ingénierie sémantique et contextuelle pour le Glossary Agent.
#     Version industrielle unifiée et immunisée contre le bruit structurel.
#     """

#     # Liste de technologies, standards et patterns d'architecture fréquents
#     ARCHITECTURAL_SIGNALS = {
#         "jwt", "rbac", "abac", "cors", "rest", "graphql", "crud", "spa", "ssr", "rsc",
#         "api", "sdk", "orm", "uuid", "ci/cd", "json", "localstorage", "sessionstorage",
#         "db", "sql", "nosql", "middleware", "webhook", "tls", "ssl", "oauth", "oidc"
#     }

#     # Dictionnaire de déduction contextuelle (Règles métiers -> Standards implicites)
#     IMPLICIT_MAPPING = {
#         r"\b(date|time|timestamp|created_at|updated_at)\b": "ISO 8601",
#         r"\b(password|hash|salt|bcrypt|argon2)\b": "Cryptographic Hashing",
#         r"\b(currency|amount|price|decimal|monetary)\b": "Fixed-Point Numeric Constraint",
#         r"\b(role|permission|admin|instructor|student|owner)\b": "Role-Based Access Control (RBAC)",
#         r"\b(origin|cross-origin|domain|header)\b": "CORS Standard"
#     }

#     @classmethod
#     def harvest_candidates(cls, parsed_data: Dict[str, Any]) -> List[str]:
#         """
#         Moissonneur universel déterministe invariant. 
#         Filtre et extrait entre 10 et 25 termes conceptuels purs sur n'importe quel type 
#         de document (Constitution, Spec, Contracts, Requirements, Plan, Tasks).
#         """
#         candidates: Set[str] = set()
#         sections = parsed_data.get("sections", [])
#         elements = parsed_data.get("elements", [])

#         # 1. Extraction et isolation dynamique du nom du projet (En-tête)
#         project_name = parsed_data.get("project_info", {}).get("project_name", "").strip()

#         # 2. Collecte sémantique récursive dans le graphe
#         for section in sections:
#             cls._extract_from_text(section.get("title", ""), candidates)
#             cls._extract_from_text(section.get("raw_content", ""), candidates)
#             cls._deduce_implicit_standards(section.get("raw_content", ""), candidates)

#         for element in elements:
#             identifier = element.get("identifier", "")
#             content = element.get("content", "")
            
#             # Ne capturer l'identifiant que s'il ne s'agit pas d'un code de ticket ou de règle interne
#             if identifier and not ("-" in identifier or "_" in identifier):
#                 if not (identifier.startswith("T") and identifier[1:].isdigit()):
#                     candidates.add(identifier.strip())
                
#             cls._extract_from_text(content, candidates)
#             cls._deduce_implicit_standards(content, candidates)

#         # 3. Normalisation initiale des chaînes (Élimination des sauts de ligne et numérotations)
#         pre_clean = set()
#         for term in candidates:
#             clean_term = term.replace("\n", " ").strip()
#             clean_term = re.sub(r'\s+\d+$', '', clean_term)  # Supprime les résidus "resend 3"
#             if len(clean_term) >= 2 and not clean_term.isdigit():
#                 pre_clean.add(clean_term)

#         # 4. MATRICE RIGIDE D'EXCLUSION DES BRUITS LOGICIELS ET TEXTUELS
#         EXCLUSION_MATRIX = {
#             # Plomberie réseau, Verbes HTTP et Transport
#             "get", "post", "put", "delete", "patch", "options", "head", "http", "https", 
#             "url", "uri", "base url", "content-type", "authorization header", "response envelope",
#             "application/json", "mime", "host", "port", "endpoint", "endpoints", "route", "routes",
#             # Expressions logiques Gherkin et Seuils Métiers
#             "given", "when", "then", "and", "but", "between", "reaches", "at least", 
#             "greater", "less", "equals", "must", "should", "contains", "from 0", "and 100", 
#             "between 0", "reaches 100", "least 90", "not 0", "after", "async throughout", "auth first",
#             # Métadonnées, Statuts documentaires et Suivi Qualité
#             "purpose", "needs", "status", "created", "ratified", "amended", "governance", 
#             "last amended", "acceptance scenarios", "independent test", "feature branch",
#             "stack", "core", "auth", "test", "app", "main", "total", "ok", "true", "false", 
#             "project", "version", "step", "tl", "dr", "tl;dr", "checklist", "priority", "p1", "p2", "p3",
#             # Variables d'exécution locales et Types génériques
#             "limit", "skip", "page", "offset", "client", "async_session", "session", "fixture", "fixtures",
#             "emailstr", "str", "int", "float", "bool", "dict", "list", "set", "tuple", "t", "jsonresponse"
#         }
        
#         DOCUMENT_ABBREVIATIONS = {"fr", "sc", "us", "con", "asm", "ii", "iii", "iv", "v", "vi"}
#         ROMAN_NUMERALS_REGEX = re.compile(r'^[IVXLC]+$', re.IGNORECASE)
#         normalized_map = {}

#         for term in pre_clean:
#             term_lower = term.lower()
#             words = term_lower.split()

#             # Filtrage du nom de projet racine
#             if project_name and (term_lower == project_name.lower() or term_lower == f"{project_name.lower()} api"):
#                 continue

#             # Filtrage des URIs et fragments de chemins réseau (ex: /api/v1)
#             if term.startswith("/") or "\\" in term:
#                 continue

#             # Filtrage des extensions de fichiers et répertoires de code (ex: conftest.py)
#             if any(term_lower.endswith(ext) for ext in [".py", ".md", ".json", ".yaml", ".yml", "/"]):
#                 continue

#             # Filtrage des marqueurs de phases (ex: Phase 1, Task 2)
#             if term_lower.startswith("phase") or "phase" in words or term_lower.startswith("task"):
#                 continue

#             # Filtrage des clés topologiques pures composées en MAJUSCULES (ex: STACK-CORE)
#             if ("-" in term or "_" in term) and term.isupper():
#                 continue

#             # Filtrage des signatures d'exécution et syntaxes de code brut
#             if any(char in term for char in ["(", ")", "[", "]", "{", "}", "...", "=", ":"]):
#                 continue

#             # Validation contre les matrices d'exclusions statiques
#             if term_lower in EXCLUSION_MATRIX or term_lower in DOCUMENT_ABBREVIATIONS:
#                 continue

#             # Validation contre les chiffres romains
#             if ROMAN_NUMERALS_REGEX.match(term):
#                 continue

#             # Validation contre les fragments asymétriques textuels (ex: "a 15", "the 0")
#             if any(len(w) == 1 and not w.isdigit() for w in words):
#                 continue

#             # Validation contre les valeurs numériques isolées faisant office de seuils
#             if any(word.isdigit() for word in words) and not any(tech in term_lower for tech in ["python", "postgresql", "sqlalchemy", "16", "3.12", "2.0"]):
#                 continue

#             # Déduplication intelligente de la casse (L'acronyme en MAJUSCULE écrase les déclinaisons)
#             if term_lower in normalized_map:
#                 if term.isupper() and not normalized_map[term_lower].isupper():
#                     normalized_map[term_lower] = term
#             else:
#                 normalized_map[term_lower] = term

#         return sorted(list(set(normalized_map.values())))

#     @classmethod
#     def _extract_from_text(cls, text: str, candidate_set: Set[str]) -> None:
#         if not text:
#             return

#         # Pattern A : Acronymes standardisés (2 à 6 capitales)
#         acronyms = re.findall(r"\b[A-Z]{2,6}\b", text)
#         for acro in acronyms:
#             candidate_set.add(acro)

#         # Pattern B : PascalCase / CamelCase
#         camel_cases = re.findall(r"\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b", text)
#         for camel in camel_cases:
#             candidate_set.add(camel)

#         # Pattern C : Runtimes typés et versions (ex: PostgreSQL 16)
#         tech_versions = re.findall(r"\b[A-Za-z]{3,}(?:\.[A-Za-z]+)?\s?\d+(?:\.\d+)*\+?\b", text)
#         for tech in tech_versions:
#             candidate_set.add(tech.strip())

#         # Pattern D : Artefacts de mise en valeur Markdown textuels
#         inline_highlights = re.findall(r"`([^`]+)`|\*\*([^*]+)\*\*", text)
#         for match in inline_highlights:
#             highlighted = match[0] if match[0] else match[1]
#             if highlighted and len(highlighted.strip().split()) <= 2:
#                 if not (highlighted.endswith(".py") or "/" in highlighted):
#                     candidate_set.add(highlighted.strip())

#         # Pattern E : Mots clés isolés correspondants à nos signaux
#         words = re.findall(r"\b[a-zA-Z\-]+\b", text.lower())
#         for word in words:
#             if word in cls.ARCHITECTURAL_SIGNALS:
#                 if word in ["jwt", "rbac", "abac", "cors", "crud", "spa", "ssr", "rsc", "api", "sdk", "orm", "uuid", "json", "tls", "ssl", "oauth", "oidc"]:
#                     candidate_set.add(word.upper())
#                 elif word == "localstorage":
#                     candidate_set.add("LocalStorage")
#                 elif word == "sessionstorage":
#                     candidate_set.add("SessionStorage")
#                 else:
#                     candidate_set.add(word.capitalize())

#     @classmethod
#     def _deduce_implicit_standards(cls, text: str, candidate_set: Set[str]) -> None:
#         """
#         Analyse le texte pour y détecter des besoins induits et injecter des standards technologiques.
#         """
#         if not text:
#             return

#         text_lower = text.lower()
#         for regex, implicit_term in cls.IMPLICIT_MAPPING.items():
#             if re.search(regex, text_lower):
#                 candidate_set.add(implicit_term)
