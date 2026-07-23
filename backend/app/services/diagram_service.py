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

    CRITICAL_ERROR_PATTERNS = {
        "flowchart": [
            # Noeud sans ID explicite
            (r'^\s*[\[\{\(][^"\w]', "Missing node ID prefix"),             # Crochets mal fermes             (r'\[[^\]]*$', "Unclosed bracket in node definition"),             # Accolades mal fermees             (r'\{[^\}]*$', "Unclosed brace in node definition"),             # Fleche mal formee sans cible             (r'-->[\s]*$', "Dangling arrow without target"),             # Sous-graphe vide sans identifiant             (r'^\s*subgraph\s*$', "Empty subgraph declaration"),         ],         "sequenceDiagram": [             (r'^\s*participant\s*$', "Empty participant declaration"),             (r'->>[^\s]', "Invalid sequence arrow syntax"),             (r'actor\s*$', "Empty actor declaration"),         ],         "erDiagram": [             (r'\Vert{}\Vert{}--\Vert{}\Vert{}', "Missing cardinality in relationship"),             (r'^\s+\w+\s*$', "Attribute missing type declaration"),             (r'^\s*\+\s*\w+\s*:\s*\w+', "UML notation forbidden in erDiagram"),         ],         "classDiagram": [             (r'^\s*class\s*$', "Empty class declaration"),             (r'\(\)\s*\{', "Invalid method syntax"),
        ],
        "stateDiagram": [
            (r'^\s*state\s*$', "Empty state declaration"),
            (r'-->\s*$', "Dangling state transition"),
        ]
    }

    GLOBAL_ERROR_PATTERNS = [
        (r'[\x00-\x08\x0b-\x0c\x0e-\x1f]', "Control characters detected"),
        (r'\(\(\s*\)\)', "Empty stadium shape"),
    ]

    @classmethod
    def validate_with_regex(cls, mermaid_code: str, diagram_type: str) -> Tuple[bool, List[str]]:
        """
        Validation deterministe par expressions regulieres.
        Retourne (is_valid, list_of_errors).
        """
        errors = []

        if not mermaid_code or not mermaid_code.strip():
            return False, ["Empty diagram code"]

        code_clean = mermaid_code.strip()
        lines = [line for line in code_clean.split('\n') if line.strip()]

        if not lines:
            return False, ["Empty diagram code"]

        # Verification 1: En-tete du diagramme (premiere ligne non vide)
        first_line = lines[0].strip().lower()
        valid_headers = [
            "flowchart", "graph", "sequencediagram", "classdiagram", 
            "erdiagram", "statediagram", "gantt", "mindmap", "pie"
        ]
        if not any(first_line.startswith(h) for h in valid_headers):
            errors.append(f"Invalid or missing diagram type header: '{lines[0]}'")

        # Verification 2: Patterns globaux
        for pattern, error_msg in cls.GLOBAL_ERROR_PATTERNS:
            if re.search(pattern, code_clean, re.MULTILINE):
                errors.append(f"Global syntax error: {error_msg}")

        # Verification 3: Patterns specifiques au type
        type_patterns = cls.CRITICAL_ERROR_PATTERNS.get(diagram_type, [])
        for pattern, error_msg in type_patterns:
            for i, line in enumerate(lines, 1):
                if re.search(pattern, line, re.IGNORECASE):
                    errors.append(f"Line {i}: {error_msg} -> '{line.strip()}'")

        # Verification 4: Extraction des noeuds declares et references (ancrage)
        declared_ids = set()
        referenced_ids = set()

        id_pattern = r'(\b\w+[\w\-]*)\s*[\[\{\(\"\']'
        ref_pattern = r'-->\s*(\b\w+[\w\-]*)'

        for line in lines:
            for match in re.finditer(id_pattern, line):
                declared_ids.add(match.group(1))

            for ref_match in re.finditer(ref_pattern, line):
                referenced_ids.add(ref_match.group(1))

        orphan_refs = referenced_ids - declared_ids
        if orphan_refs:
            reserved_keywords = {'subgraph', 'end', 'style', 'classDef', 'click', 'direction'}
            valid_orphans = {r for r in orphan_refs if r not in reserved_keywords}
            if valid_orphans:
                errors.append(f"Orphan node references (not declared): {valid_orphans}")

        is_valid = len(errors) == 0
        return is_valid, errors

    @classmethod
    def validate_with_mermaid_cli(cls, mermaid_code: str) -> Tuple[bool, Optional[str]]:
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
    """

    def __init__(self, strict_validation: bool = True, use_mermaid_cli: bool = False):
        self.strict_validation = strict_validation
        self.use_mermaid_cli = use_mermaid_cli
        self.validator = MermaidSyntaxValidator()

    @staticmethod
    def clean_mermaid_code(code: str) -> str:
        """
        Nettoyage et normalisation automatique du code Mermaid.js.
        """
        if not code:
            return ""

        # 1. Trim general & retrait des blocs Markdown
        code = code.strip()
        if code.startswith("```"):
            lines = code.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            code = "\n".join(lines).strip()

        # 2. Nettoyage des sous-graphes : convertit `subgraph "Nom Layer"` -> `subgraph Nom_Layer`
        def fix_subgraph(match):
            raw_title = match.group(1).strip()
            cleaned_title = re.sub(r'[^\w]', '_', raw_title)
            return f"subgraph {cleaned_title}"

        code = re.sub(r'subgraph\s+"([^"]+)"', fix_subgraph, code)
        code = re.sub(r'subgraph\s+\'([^\']+)\'', fix_subgraph, code)

        # 3. Formes de noeuds incompatibles
        code = re.sub(r'\(\[([^\]]+)\]\)', r'[\1]', code)
        code = re.sub(r'\(\(([^)]+)\)\)', r'[\1]', code)
        code = re.sub(r'\[\[([^\]]+)\]\]', r'[\1]', code)
        code = re.sub(r'\{\{([^}]+)\}\}', r'{\1}', code)

        # 4. Correction des fleches
        code = re.sub(r'-->\|([^|]+)\|>', r'-->|\1|', code)

        # 5. Conversion attributs ERDiagram style UML
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
        all_errors = []

        is_regex_valid, regex_errors = self.validator.validate_with_regex(
            diagram.mermaid_code, 
            diagram.type
        )
        all_errors.extend(regex_errors)

        if not is_regex_valid and self.strict_validation:
            return False, all_errors

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
        ParsingAgentOutput(**parsed_json_dict)

        system_prompt = get_diagram_agent_prompt(
            diagram_spec=diagram_spec_dict,
            parsed_project_data=parsed_json_dict
        )

        user_prompt = json.dumps(parsed_json_dict, ensure_ascii=False)

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
        diagram_doc = parse_and_validate_json(raw_output, DiagramOutputModel)

        sanitized_items: List[DiagramItem] = []
        skipped_count = 0

        for diag in diagram_doc.diagrams:
            cleaned_code = self.clean_mermaid_code(diag.mermaid_code)

            candidate = DiagramItem(
                title=diag.title,
                type=diag.type,
                description=diag.description,
                mermaid_code=cleaned_code
            )

            is_valid, errors = self._validate_diagram(candidate)

            if is_valid:
                sanitized_items.append(candidate)
            else:
                skipped_count += 1
                print(f"[DiagramAgentService] SKIPPED diagram '{diag.title}' ({diag.type}) due to syntax errors:")
                for err in errors:
                    print(f"  - {err}")

        total_generated = len(diagram_doc.diagrams)
        valid_count = len(sanitized_items)
        print(f"[DiagramAgentService] Validation complete: {valid_count}/{total_generated} diagrams passed ({skipped_count} skipped)")

        final_items = sanitized_items[:4]
        return DiagramOutputModel(diagrams=final_items)