# app/services/diagram_service.py
import json
import re
from typing import Dict, Any, List, Optional, Tuple
import subprocess
import tempfile
import os

# Importations des schemas requis
from app.schemas.diagram_agent_schema import DiagramOutputModel, DiagramItem
from app.schemas.parsing_agent_schema import ParsingAgentOutput

# Importations des composants d'infrastructure
from app.core.prompts import get_diagram_agent_prompt
from app.core.llm_client import ollama_chat, get_llm_model
from app.core.llm_utils import parse_and_validate_json


class MermaidSyntaxValidator:
    """
    Validateur de syntaxe Mermaid.js multi-niveau.
    Combine validation regex deterministe et validation par mermaid-cli (optionnel).
    """

    # Patterns de detection d'erreurs critiques par type de diagramme
    CRITICAL_ERROR_PATTERNS = {
        "flowchart": [
            # Noeud sans ID explicite (commence par [ ou { sans mot avant)
            (r'^\s*[\[\{\(][^"\w]', "Missing node ID prefix"),
            # Crochets mal fermes
            (r'\[[^\]]*$', "Unclosed bracket in node definition"),
            # Accolades mal fermees
            (r'\{[^\}]*$', "Unclosed brace in node definition"),
            # Fleche mal formee sans cible
            (r'-->[\s]*$', "Dangling arrow without target"),
            # Syntaxe de sous-graphe invalide
            (r'subgraph\s+[^\s]', "Invalid subgraph syntax"),
        ],
        "sequenceDiagram": [
            # Participant mal defini
            (r'^\s*participant\s*$', "Empty participant declaration"),
            # Fleche de sequence invalide
            (r'->>[^\s]', "Invalid sequence arrow syntax"),
            # Acteur sans nom
            (r'actor\s*$', "Empty actor declaration"),
        ],
        "erDiagram": [
            # Relation sans cardinalite
            (r'\|\|--\|\|', "Missing cardinality in relationship"),
            # Attribut sans type
            (r'^\s+\w+\s*$', "Attribute missing type declaration"),
            # Syntaxe UML interdite (+id: int)
            (r'^\s*\+\s*\w+\s*:\s*\w+', "UML notation forbidden in erDiagram"),
        ],
        "classDiagram": [
            # Classe sans nom
            (r'^\s*class\s*$', "Empty class declaration"),
            # Methode mal formee
            (r'\(\)\s*\{', "Invalid method syntax"),
        ],
        "stateDiagram": [
            # Etat sans nom
            (r'^\s*state\s*$', "Empty state declaration"),
            # Transition sans cible
            (r'-->\s*$', "Dangling state transition"),
        ]
    }

    # Patterns globaux (appliques a tous les types)
    GLOBAL_ERROR_PATTERNS = [
        # Ligne vide au debut (diagram type doit etre en premiere ligne)
        (r'^\s*\n', "Leading whitespace before diagram declaration"),
        # Caracteres de controle
        (r'[\x00-\x08\x0b-\x0c\x0e-\x1f]', "Control characters detected"),
        # Guillemets non echappes dans les labels
        (r'\["[^"]*"[^"]*"[^"]*"\]', "Unescaped quotes in node label"),
        # Parentheses imbriquees incorrectes
        (r'\(\([^\)]*\([^\)]*\)\)', "Nested parentheses in stadium shape (forbidden)"),
        # Double crochets (forme interdite)
        (r'\[\[', "Double bracket shape forbidden"),
        # Double accolades (forme interdite)
        (r'\{\{', "Double brace shape forbidden"),
    ]

    @classmethod
    def validate_with_regex(cls, mermaid_code: str, diagram_type: str) -> Tuple[bool, List[str]]:
        """
        Validation deterministe par expressions regulieres.
        Retourne (is_valid, list_of_errors).
        """
        errors = []
        lines = mermaid_code.split('\n')

        # Verification 1: Le code ne doit pas etre vide
        if not mermaid_code or not mermaid_code.strip():
            return False, ["Empty diagram code"]

        # Verification 2: La premiere ligne doit declarer le type de diagramme
        first_line = lines[0].strip().lower()
        valid_headers = ["flowchart", "sequencediagram", "classdiagram", "erdiagram", 
                        "statediagram", "gantt", "mindmap", "pie"]
        if not any(first_line.startswith(h) for h in valid_headers):
            errors.append(f"Invalid or missing diagram type header: '{lines[0]}'")

        # Verification 3: Patterns globaux
        for pattern, error_msg in cls.GLOBAL_ERROR_PATTERNS:
            if re.search(pattern, mermaid_code, re.MULTILINE):
                errors.append(f"Global syntax error: {error_msg}")

        # Verification 4: Patterns specifiques au type
        type_patterns = cls.CRITICAL_ERROR_PATTERNS.get(diagram_type, [])
        for pattern, error_msg in type_patterns:
            for i, line in enumerate(lines, 1):
                if re.search(pattern, line, re.IGNORECASE):
                    errors.append(f"Line {i}: {error_msg} -> '{line.strip()}'")

        # Verification 5: Noeuds flowchart sans ID (pattern special multi-ligne)
        if diagram_type == "flowchart":
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped and stripped[0] in '[{"(' and not re.match(r'^\w+', stripped):
                    if not stripped.startswith('subgraph') and not stripped.startswith('end'):
                        errors.append(f"Line {i}: Node definition missing ID prefix -> '{stripped}'")

        # Verification 6: Verification des identifiants de noeuds (traceabilite)
        declared_ids = set()
        referenced_ids = set()

        id_pattern = r'^\s*(\w+[\w\-]*)\s*[\[\{\(\"\']'
        ref_pattern = r'-->\s*(\w+[\w\-]*)'

        for line in lines:
            match = re.match(id_pattern, line)
            if match:
                declared_ids.add(match.group(1))

            for ref_match in re.finditer(ref_pattern, line):
                referenced_ids.add(ref_match.group(1))

        orphan_refs = referenced_ids - declared_ids
        if orphan_refs:
            valid_orphans = {r for r in orphan_refs if r not in ['subgraph', 'end', 'style', 'classDef']}
            if valid_orphans:
                errors.append(f"Orphan node references (not declared): {valid_orphans}")

        is_valid = len(errors) == 0
        return is_valid, errors

    @classmethod
    def validate_with_mermaid_cli(cls, mermaid_code: str) -> Tuple[bool, Optional[str]]:
        """
        Validation via mermaid-cli (mmdc) si disponible.
        Plus lente mais plus fiable pour les cas complexes.
        """
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.mmd', delete=False) as f:
                f.write(mermaid_code)
                temp_path = f.name

            result = subprocess.run(
                ['mmdc', '-i', temp_path, '-o', '/dev/null'],
                capture_output=True,
                text=True,
                timeout=10
            )

            os.unlink(temp_path)

            if result.returncode != 0:
                return False, result.stderr
            return True, None

        except FileNotFoundError:
            return True, None
        except Exception:
            return True, None


class DiagramAgentService:
    """
    Service d'orchestration pour le Diagram Agent.
    Exploite le client Ollama/OpenAI-compatible centralise pour analyser la topologie
    du document parse et generer des schemas d'architecture Mermaid.js valides.
    """

    def __init__(self, strict_validation: bool = True, use_mermaid_cli: bool = False):
        """
        Args:
            strict_validation: Si True, rejette les diagrammes avec des erreurs regex detectees.
            use_mermaid_cli: Si True, tente une validation secondaire avec mermaid-cli.
        """
        self.strict_validation = strict_validation
        self.use_mermaid_cli = use_mermaid_cli
        self.validator = MermaidSyntaxValidator()

    @staticmethod
    def clean_mermaid_code(code: str) -> str:
        """
        Applique une serie de correctifs Regex deterministes sur le code Mermaid.js
        pour eliminer les erreurs courantes de syntaxe generees par le LLM.
        """
        if not code:
            return ""

        # 1. Suppression des balises markdown eventuelles
        code = code.strip()
        if code.startswith("```"):
            lines = code.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            code = "\n".join(lines)

        # 2. Correction des formes de noeuds incompatibles avec les moteurs de rendu
        code = re.sub(r'\(\[([^\]]+)\]\)', r'[\1]', code)
        code = re.sub(r'\(\(([^)]+)\)\)', r'[\1]', code)
        code = re.sub(r'\[\[([^\]]+)\]\]', r'[\1]', code)
        code = re.sub(r'\{\{([^}]+)\}\}', r'{\1}', code)

        # 3. Correction des fleches mal formees (ex: -->|label|> vers -->|label|)
        code = re.sub(r'-->\|([^|]+)\|>', r'-->|\1|', code)

        # 4. Correction des attributs erDiagram en style UML (+id: int vers int id)
        lines = code.split('\n')
        fixed_lines = []
        in_entity_block = False

        for line in lines:
            stripped = line.strip()

            if re.match(r'^[A-Za-z_][A-Za-z0-9_]*\s*\{', stripped):
                in_entity_block = True
                fixed_lines.append(line)
                continue
            if stripped == "}" and in_entity_block:
                in_entity_block = False
                fixed_lines.append(line)
                continue

            if in_entity_block:
                match1 = re.match(r'^\+?\s*(\w+)\s*:\s*(\w+)\s*(PK|FK)?\s*$', stripped)
                if match1:
                    field_name, type_name, key_marker = match1.group(1), match1.group(2), match1.group(3) or ''
                    fixed = f"{type_name} {field_name}" + (f" {key_marker}" if key_marker else "")
                    leading = line[:len(line) - len(line.lstrip())]
                    fixed_lines.append(leading + fixed)
                    continue

            fixed_lines.append(line)

        return "\n".join(fixed_lines).strip()

    def _validate_diagram(self, diagram: DiagramItem) -> Tuple[bool, List[str]]:
        """
        Valide un diagramme individuel selon les regles configurees.
        Retourne (is_valid, error_messages).
        """
        all_errors = []

        # Etape 1: Validation regex deterministe (toujours executee)
        is_regex_valid, regex_errors = self.validator.validate_with_regex(
            diagram.mermaid_code, 
            diagram.type
        )
        all_errors.extend(regex_errors)

        if not is_regex_valid and self.strict_validation:
            return False, all_errors

        # Etape 2: Validation mermaid-cli (optionnelle)
        if self.use_mermaid_cli and is_regex_valid:
            is_cli_valid, cli_error = self.validator.validate_with_mermaid_cli(diagram.mermaid_code)
            if not is_cli_valid and cli_error:
                all_errors.append(f"Mermaid CLI validation failed: {cli_error}")
                return False, all_errors

        return len(all_errors) == 0, all_errors

    def generate_diagrams(
        self, 
        parsed_json_dict: Dict[str, Any], 
        diagram_spec_dict: Dict[str, Any]
    ) -> DiagramOutputModel:
        """
        Execute le pipeline complet de generation de diagrammes d'architecture.
        Les diagrammes avec erreurs de syntaxe sont automatiquement filtres.
        """
        # 1. Validation structurelle de l'objet d'entree (ParsingAgentOutput)
        ParsingAgentOutput(**parsed_json_dict)

        # 2. Construction du Prompt Systeme enrichi
        system_prompt = get_diagram_agent_prompt(
            diagram_spec=diagram_spec_dict,
            parsed_project_data=parsed_json_dict
        )

        # 3. Payload d'entree utilisateur (JSON parse epure)
        user_prompt = json.dumps(parsed_json_dict, ensure_ascii=False)

        # 4. Inference LLM via le client centralise
        response = ollama_chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=8192
        )

        raw_output = response

        # 5. Extraction Regex et validation Pydantic
        diagram_doc = parse_and_validate_json(raw_output, DiagramOutputModel)

        # 6. Post-traitement, nettoyage et FILTRAGE des diagrammes errones
        sanitized_items: List[DiagramItem] = []
        skipped_count = 0

        for diag in diagram_doc.diagrams:
            # Nettoyage du code
            cleaned_code = self.clean_mermaid_code(diag.mermaid_code)

            # Creation du diagramme nettoye
            candidate = DiagramItem(
                title=diag.title,
                type=diag.type,
                description=diag.description,
                mermaid_code=cleaned_code
            )

            # Validation de la syntaxe
            is_valid, errors = self._validate_diagram(candidate)

            if is_valid:
                sanitized_items.append(candidate)
            else:
                skipped_count += 1
                # Log de l'erreur pour debug (dans un vrai systeme, utiliser logger)
                print(f"[DiagramAgentService] SKIPPED diagram '{diag.title}' ({diag.type}) due to syntax errors:")
                for err in errors:
                    print(f"  - {err}")

        # Log du resultat du filtrage
        total_generated = len(diagram_doc.diagrams)
        valid_count = len(sanitized_items)
        print(f"[DiagramAgentService] Validation complete: {valid_count}/{total_generated} diagrams passed ({skipped_count} skipped)")

        # Limiter le resultat a 4 diagrammes maximum
        final_items = sanitized_items[:4]

        return DiagramOutputModel(diagrams=final_items)