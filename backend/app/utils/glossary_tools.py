import re
from typing import Dict, Any, List, Set

class GlossaryHarvesterService:
    """
    Outil d'ingénierie sémantique et contextuelle pour le Glossary Agent.
    Analyse le document parsé pour en extraire de manière déterministe les termes,
    acronymes, entités structurelles et standards implicites avant l'inférence LLM.
    """

    # Liste de technologies, standards et patterns d'architecture fréquents à surveiller
    ARCHITECTURAL_SIGNALS = {
        "jwt", "rbac", "abac", "cors", "rest", "graphql", "crud", "spa", "ssr", "rsc",
        "api", "sdk", "orm", "uuid", "ci/cd", "json", "localstorage", "sessionstorage",
        "db", "sql", "nosql", "middleware", "webhook", "tls", "ssl", "oauth", "oidc"
    }

    # Dictionnaire de déduction contextuelle (Règles métiers -> Standards implicites)
    IMPLICIT_MAPPING = {
        r"\b(date|time|timestamp|created_at|updated_at)\b": "ISO 8601",
        r"\b(password|hash|salt|bcrypt|argon2)\b": "Cryptographic Hashing",
        r"\b(currency|amount|price|decimal|monetary)\b": "Fixed-Point Numeric Constraint",
        r"\b(role|permission|admin|instructor|student|owner)\b": "Role-Based Access Control (RBAC)",
        r"\b(origin|cross-origin|domain|header)\b": "CORS Standard"
    }

    @classmethod
    def harvest_candidates(cls, parsed_data: Dict[str, Any]) -> List[str]:
        """
        Analyse le JSON issu du Parsing Agent et extrait la liste unique
        des termes candidats impératifs classés par pertinence contextuelle.
        """
        candidates: Set[str] = set()
        sections = parsed_data.get("sections", [])

        # 1. Extraction depuis les métadonnées et titres de sections
        project_name = parsed_data.get("project_info", {}).get("project_name")
        if project_name and project_name.lower() not in ["inconnu", "unknown", ""]:
            candidates.add(project_name)

        for section in sections:
            title = section.get("title", "")
            content = section.get("raw_content", "")
            
            # Extraction directe dans les titres (Entités métiers fortes)
            cls._extract_from_text(title, candidates)
            # Extraction dans le corps du texte
            cls._extract_from_text(content, candidates)
            # Déduction des concepts implicites basée sur les règles du texte
            cls._deduce_implicit_standards(content, candidates)

        # Nettoyage final : suppression des nombres purs ou tokens trop courts (< 2 caractères)
        clean_candidates = [
            term for term in candidates 
            if len(term) >= 2 and not term.isdigit() and term.lower() not in ["the", "and", "for"]
        ]

        # Tri alphabétique pour garantir le déterminisme lors des tests unitaires
        return sorted(list(set(clean_candidates)))

    @classmethod
    def _extract_from_text(cls, text: str, candidate_set: Set[str]) -> None:
        """
        Applique les patterns d'extraction syntaxique sur un bloc de texte brut.
        """
        if not text:
            return

        # Pattern A : Acronymes purs en majuscules (2 à 6 lettres) -> JWT, RBAC, API
        acronyms = re.findall(r"\b[A-Z]{2,6}\b", text)
        for acro in acronyms:
            candidate_set.add(acro)

        # Pattern B : Structures CamelCase / PascalCase (Entités et Contraintes) -> LocalStorage, ActiveEnrollmentConstraint
        camel_cases = re.findall(r"\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b", text)
        for camel in camel_cases:
            candidate_set.add(camel)

        # Pattern C : Technologies nommées avec des spécifications de versioning -> Python3.12, Next.js, PostgreSQL16
        tech_versions = re.findall(r"\b[A-Za-z]+(?:\.[A-Za-z]+)?\s?\d+(?:\.\d+)*\+?\b", text)
        for tech in tech_versions:
            candidate_set.add(tech.strip())

        # Pattern D : Mots mis en valeur en Markdown (Gras ou Code inline) -> **Expense**, `src/server`
        inline_highlights = re.findall(r"`([^`]+)`|\*\*([^*]+)\*\*", text)
        for match in inline_highlights:
            highlighted = match[0] if match[0] else match[1]
            # On ne garde que si c'est un mot unique ou un token technique court
            if highlighted and len(highlighted.split()) <= 2:
                candidate_set.add(highlighted.strip())

        # Pattern E : Interception des mots-clés de notre dictionnaire de signaux d'architecture
        words = re.findall(r"\b[a-zA-Z\-]+\b", text.lower())
        for word in words:
            if word in cls.ARCHITECTURAL_SIGNALS:
                # On ré-injecte le mot en conservant une casse propre ou majuscule pour les acronymes connus
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
        """
        Analyse le texte pour y détecter des besoins induits et injecter des standards technologiques.
        """
        if not text:
            return

        text_lower = text.lower()
        for regex, implicit_term in cls.IMPLICIT_MAPPING.items():
            if re.search(regex, text_lower):
                candidate_set.add(implicit_term)