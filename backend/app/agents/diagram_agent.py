import json
import re
from app.agents.llm_client import llm_client, LLMClientError

# Whitelist of diagram types that render reliably
ALLOWED_TYPES = {
    "flowchart", "sequenceDiagram", "classDiagram", "erDiagram",
    "stateDiagram", "gantt", "mindmap", "pie"
}

SYSTEM_PROMPT = """You are a Diagram Agent. Analyze the parsed document and generate accurate, semantically correct Mermaid diagrams.

You may ONLY use these diagram types:
- flowchart (processes, workflows, user flows, requirements traceability)
- sequenceDiagram (interactions between actors/systems over time — MANDATORY when API/user-system interactions exist)
- classDiagram (entities with attributes and methods)
- erDiagram (database entity relationships — use ONLY for data models)
- stateDiagram (state machines, lifecycles)
- gantt (timelines, schedules, milestones)
- mindmap (hierarchical concepts)
- pie (proportional data)

=== DIAGRAM SELECTION RULES ===

1. ALWAYS generate a sequenceDiagram when the document describes:
   - API interactions between users and a system
   - Request/response flows between actors
   - Any multi-step interaction involving different roles (Instructor, Student, System)
   The sequenceDiagram is NOT optional when interactions exist.

2. For requirements traceability: ALWAYS use flowchart with subgraphs.

3. For data models: ALWAYS use erDiagram, NEVER classDiagram.

4. For workflows: NEVER generate purely linear flowcharts.

=== CRITICAL ACCURACY RULES ===

1. REQUIREMENTS TRACEABILITY (flowchart with subgraphs):
   - User Stories IMPLEMENT / TRACE TO Requirements.
   - CORRECT arrow direction: US1 -->|traces to| FR1 (UserStory → Requirement)
   - ALWAYS include the FULL TEXT in node labels, not just IDs.
     WRONG: US1[US-1] or FR1[FR-001]
     CORRECT: US1[US-1: Instructor creates course] or FR1[FR-001: Create courses]
   - Use subgraphs to group Requirements and UserStories.

2. ENTITY RELATIONSHIPS — erDiagram (NOT classDiagram):
   - For database/data models: ALWAYS use erDiagram, NEVER use classDiagram.

   erDiagram RELATIONSHIP syntax:
     ENTITY1 cardinality relationship cardinality ENTITY2 : "label"
     Cardinalities: || (one), |{ (many), o| (zero or one), o{ (zero or many)
     Example: USER ||--o{ ENROLLMENT : "enrolls as"

   erDiagram ATTRIBUTE syntax (CRITICAL — different from classDiagram):
     CORRECT:
       USER {
         int id PK
         string email
         string name
         string role
       }

     WRONG (classDiagram style — NEVER use in erDiagram):
       USER {
         +id: int
         +email: string
       }

   Rules:
   - Attributes: type field_name (e.g., "int id", "string email")
   - NO plus signs (+), NO colons (:), NO type after field name
   - PK/FK markers go after the field name: "int id PK", "int course_id FK"
   - NEVER mix UML association notation with ER notation.

3. WORKFLOW DIAGRAMS — MANDATORY COMPLEXITY (flowchart):

   PURELY LINEAR WORKFLOWS ARE FORBIDDEN. Every workflow MUST contain:
   - At least ONE decision diamond: DEC{Decision?}
   - At least ONE loop (arrow going back to a previous step)
   - At least ONE alternative path (Yes/No branch that doesn't just continue forward)

   EXAMPLE of a CORRECT workflow (copy this pattern):

   flowchart TD
       START[Start] --> CREATE[Create course]
       CREATE --> ADD_MODULES[Add modules]
       ADD_MODULES --> MORE{More modules?}
       MORE -->|Yes| ADD_MODULES
       MORE -->|No| VALIDATE{Valid?}
       VALIDATE -->|No| EDIT[Edit course]
       EDIT --> VALIDATE
       VALIDATE -->|Yes| PUBLISH[Publish course]
       PUBLISH --> MANAGE[Manage course]
       MANAGE --> NEEDS_UPDATE{Needs update?}
       NEEDS_UPDATE -->|Yes| UPDATE[Update course]
       UPDATE --> MANAGE
       NEEDS_UPDATE -->|No| ARCHIVE{Archive?}
       ARCHIVE -->|Yes| DELETE[Delete course]
       ARCHIVE -->|No| MANAGE
       DELETE --> END[End]

   WRONG (purely linear — NEVER do this):

   flowchart TD
       [Start] --> [Create course]
       [Create course] --> [Add modules]
       [Add modules] --> [Publish course]
       [Publish course] --> [Manage course]
       [Manage course] --> [Update course]
       [Update course] --> [Delete course]
       [Delete course] --> [End]

   Rules:
   - Start and End nodes are rectangles: START[Start] and END[End]
   - Actions are rectangles: ID[Action description]
   - Decisions are diamonds: ID{Decision question?}
   - A "Delete" or "Archive" step is an ALTERNATIVE terminal, NOT sequential after update.
   - "Receive email" is NOT a user action — it is a system event.
   - System events: SYS1[System: Send welcome email]

4. MERMAID SYNTAX — ABSOLUTE REQUIREMENTS:
   EVERY node MUST have an ID prefix. This is the #1 cause of render failures.

   WRONG (will fail):
     [Start] --> [Action]
     {Decision?} -->|Yes| [Next]

   CORRECT:
     START[Start] --> ACT1[Action]
     DEC1{Decision?} -->|Yes| NEXT1[Next]

   Node ID rules:
   - Use short alphanumeric IDs: START, END, ACT1, DEC1, SYS1, etc.
   - NEVER use bare [label], {label}, or (label) without an ID.

   Allowed node shapes (ultra-compatible):
   - Rectangle: ID[text]
   - Rounded rectangle: ID(text)
   - Diamond: ID{text}

   NEVER use:
   - Circle: ((text)) — causes parse errors
   - Stadium: ([text]) — causes parse errors
   - Double brackets: [[text]] — causes parse errors
   - Hexagon: {{text}} — causes parse errors

   flowchart direction: TD or LR only.
   Subgraphs: subgraph Name ... end

5. SEQUENCE DIAGRAMS:
   - Use participant declarations.
   - Show activate/deactivate for long operations.
   - Include alt/opt/loop blocks for conditionals.
   - Example:
     sequenceDiagram
         participant Instructor
         participant Student
         participant System
         Instructor ->> System: Create course
         System -->> Instructor: Course created
         Student ->> System: Enroll in course
         System -->> Student: Enrolled

=== FLOWCHART LABEL RULES ===
When a node label contains commas, semicolons, or unmatched parentheses,
wrap the ENTIRE label in DOUBLE QUOTES:
  Brackets: PHASE1["Phase 1: Project initialization, database schema, migrations"]
  Braces:   CONFLICT{"Conflict (duplicate, constraint violation)"}
  WRONG:    PHASE1[Phase 1: Project initialization, database schema, migrations]
  WRONG:    CONFLICT{Conflict (duplicate, constraint violation)}

This is REQUIRED for labels with commas or complex punctuation in BOTH rectangles AND diamonds.

=== TECHNOLOGY STACK DIAGRAMS ===
When generating an erDiagram for a technology stack:
- The entities MUST represent ACTUAL technologies mentioned or strongly implied
  in the document (e.g., FastAPI, PostgreSQL, React, Docker, Redis, etc.).
- NEVER generate generic placeholder entities like "TECHNOLOGY" or "STACK"
  with only "name" and "version" fields.
- Each technology should be its OWN entity with relevant attributes.
- Show relationships between technologies (e.g., "backend uses", "frontend consumes",
  "database persists", "cache optimizes").

=== SYNTAX RULES ===
- flowchart: flowchart TD or LR. Nodes: A[text], B{text}. Arrows: --> or -->|label|.
  NEVER use -->|label|> — the trailing > is invalid syntax.
- sequenceDiagram: participant, actor, ->>, -->>, activate, deactivate, alt, else, end, loop, end.
- classDiagram: class Name { +type field +method() }. Relations: -->, --*, --o, ..>.
- erDiagram: ENTITY ||--o{ OTHER : "label". Attributes: ENTITY { type field PK }.

Return ONLY valid JSON. No markdown fences inside mermaid_code.
Generate 1-4 diagrams. Quality over quantity.
If no diagrammable content, return {"diagrams": []}.

Return JSON:
{
  "diagrams": [
    {
      "title": "...",
      "type": "flowchart|sequenceDiagram|classDiagram|erDiagram|stateDiagram|gantt|mindmap|pie",
      "description": "...",
      "mermaid_code": "valid raw mermaid syntax..."
    }
  ]
}
"""


def _extract_json(raw: str) -> dict:
    """Extract JSON from LLM response, handling markdown fences and trailing text."""
    text = raw.strip()

    if "```json" in text:
        parts = text.split("```json", 1)
        if len(parts) == 2:
            code_and_rest = parts[1]
            if "```" in code_and_rest:
                text = code_and_rest.split("```", 1)[0].strip()
    elif "```" in text:
        parts = text.split("```", 2)
        if len(parts) >= 3:
            text = parts[1].strip()
            first_newline = text.find("\n")
            if first_newline != -1 and " " not in text[:first_newline] and len(text[:first_newline]) < 20:
                text = text[first_newline + 1:].strip()

    if not text.startswith("{"):
        start_idx = text.find("{")
        if start_idx != -1:
            text = text[start_idx:]

    if text.startswith("{"):
        brace_count = 0
        in_string = False
        escape_next = False
        end_idx = -1

        for i, char in enumerate(text):
            if escape_next:
                escape_next = False
                continue
            if char == "\\":
                escape_next = True
                continue
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            if not in_string:
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = i
                        break

        if end_idx != -1:
            text = text[:end_idx + 1]

    return json.loads(text)


async def generate_diagrams(structured_json: dict) -> dict:
    if not isinstance(structured_json, dict):
        raise ValueError(f"Expected structured_json to be a dict, got {type(structured_json).__name__}")

    prompt_payload = json.dumps(structured_json, indent=2, ensure_ascii=False)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Generate diagrams for this parsed document:\n\n{prompt_payload}",
        },
    ]

    try:
        raw_response = await llm_client.chat_completion(messages, temperature=0.1)
    except LLMClientError:
        raise

    try:
        parsed = _extract_json(raw_response)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Diagram agent returned invalid JSON.\nError: {exc}\nRaw start: {raw_response[:800]}"
        ) from exc

    if not isinstance(parsed, dict):
        raise ValueError("Diagram agent response JSON is not an object")

    diagrams = parsed.get("diagrams", [])
    if not isinstance(diagrams, list):
        raise ValueError(f"Expected 'diagrams' to be a list, got {type(diagrams).__name__}")

    filtered = []

    for i, diag in enumerate(diagrams):
        if not isinstance(diag, dict):
            print(f"Skipping non-dict diagram at index {i}")
            continue
        diag_type = diag.get("type", "")
        if diag_type not in ALLOWED_TYPES:
            print(f"Filtering out disallowed diagram type: {diag_type}")
            continue

        mermaid_code = diag.get("mermaid_code", "")
        mermaid_code = _strip_markdown_fences(mermaid_code)
        mermaid_code = _fix_mermaid_syntax(mermaid_code)
        mermaid_code = _fix_missing_node_ids(mermaid_code)
        mermaid_code = _fix_flowchart_node_labels(mermaid_code)
        mermaid_code = _fix_flowchart_arrows(mermaid_code)
        mermaid_code = _fix_er_diagram_attributes(mermaid_code)
        mermaid_code = _fix_er_relationships(mermaid_code)

        filtered.append({
            "title": diag.get("title", f"Diagram {i + 1}"),
            "type": diag_type,
            "description": diag.get("description", ""),
            "mermaid_code": mermaid_code,
        })

    filtered = filtered[:4]
    return {"diagrams": filtered}


def _strip_markdown_fences(code: str) -> str:
    """Remove markdown code fences from mermaid code."""
    code = code.strip()
    if code.startswith("```"):
        lines = code.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        code = "\n".join(lines)
    return code.strip()


def _fix_mermaid_syntax(code: str) -> str:
    """Fix common Mermaid syntax issues that break older mmdc rendering."""
    code = re.sub(r'\(\[([^\]]+)\]\)', r'[\1]', code)
    code = re.sub(r'\(\(([^)]+)\)\)', r'[\1]', code)
    code = re.sub(r'\[\[([^\]]+)\]\]', r'[\1]', code)
    code = re.sub(r'\{\{([^}]+)\}\}', r'{\1}', code)
    return code


def _fix_missing_node_ids(code: str) -> str:
    """Fix Mermaid flowchart code where nodes lack IDs."""
    lines = code.split('\n')
    label_to_id = {}
    node_counter = 1

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("flowchart") or stripped.startswith("subgraph") or stripped == "end":
            continue

        # Collect bare bracket nodes [label]
        for match in re.finditer(r'(?<![A-Za-z0-9_])(\[[^\]]+\])', stripped):
            label = match.group(1)
            if label not in label_to_id:
                label_to_id[label] = f"N{node_counter}"
                node_counter += 1

        # Strip bracket nodes
        temp = re.sub(r'\[[^\]]+\]', '', stripped)

        # Collect bare brace nodes {label}
        for match in re.finditer(r'(?<![A-Za-z0-9_])(\{[^}]+\})', temp):
            label = match.group(1)
            if label not in label_to_id:
                label_to_id[label] = f"N{node_counter}"
                node_counter += 1

        # Strip brace nodes too BEFORE matching parens
        temp = re.sub(r'\{[^}]+\}', '', temp)

        # Now collect bare paren nodes (label) - won't match nested ones
        for match in re.finditer(r'(?<![A-Za-z0-9_])(\([^)]+\))', temp):
            label = match.group(1)
            if label not in label_to_id:
                label_to_id[label] = f"N{node_counter}"
                node_counter += 1

    if not label_to_id:
        return code

    fixed_lines = []
    for line in lines:
        fixed_line = line
        for label, nid in sorted(label_to_id.items(), key=lambda x: len(x[0]), reverse=True):
            escaped_label = re.escape(label)
            fixed_line = re.sub(r'(?<![A-Za-z0-9_])' + escaped_label, f"{nid}{label}", fixed_line)
        fixed_lines.append(fixed_line)

    return '\n'.join(fixed_lines)


def _fix_flowchart_node_labels(code: str) -> str:
    """
    Fix flowchart node labels containing commas, brackets, or special chars by wrapping in quotes.
    Handles BOTH bracket [label] and brace {label} nodes.
    """
    lines = code.split('\n')
    fixed_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("flowchart") or stripped.startswith("subgraph") or stripped == "end":
            fixed_lines.append(line)
            continue

        # Fix bracket nodes [label] with proper nested bracket handling
        fixed_line = _fix_bracket_nodes(line)

        # Fix brace nodes {label} (decision diamonds)
        def fix_brace_node(match):
            full = match.group(0)
            node_id = match.group(1)
            label = match.group(2)
            if '"' in label:
                return full
            if re.search(r'[,;\[\]]', label) or label.count('(') != label.count(')'):
                safe_label = label.replace('"', '\\"')
                return f'{node_id}{{"{safe_label}"}}'
            return full

        fixed_line = re.sub(
            r'([A-Za-z_][A-Za-z0-9_]*)\{([^}]+)\}',
            fix_brace_node,
            fixed_line
        )

        fixed_lines.append(fixed_line)

    return '\n'.join(fixed_lines)

def _fix_bracket_nodes(line: str) -> str:
    """Parse a line and fix bracket nodes, handling nested brackets correctly."""
    result = []
    i = 0
    while i < len(line):
        # Fast path: copy non-matching chars
        if not (line[i].isalpha() or line[i] == '_'):
            result.append(line[i])
            i += 1
            continue

        # Try to match an identifier followed by [
        id_match = re.match(r'[A-Za-z_][A-Za-z0-9_]*', line[i:])
        if not id_match:
            result.append(line[i])
            i += 1
            continue

        node_id = id_match.group(0)
        after_id = i + len(node_id)
        if after_id >= len(line) or line[after_id] != '[':
            result.append(line[i])
            i += 1
            continue

        # Found ID[ — now find matching ] with bracket depth tracking
        start = after_id + 1
        depth = 1
        j = start
        while j < len(line) and depth > 0:
            if line[j] == '[':
                depth += 1
            elif line[j] == ']':
                depth -= 1
            j += 1

        if depth != 0:
            result.append(line[i])
            i += 1
            continue

        label = line[start:j-1]
        needs_quotes = (
            '"' not in label and
            (re.search(r'[,;\[\]]', label) or label.count('(') != label.count(')'))
        )

        if needs_quotes:
            result.append(f'{node_id}["{label.replace(chr(34), chr(92)+chr(34))}"]')
        else:
            result.append(f'{node_id}[{label}]')

        i = j

    return ''.join(result)

def _fix_flowchart_arrows(code: str) -> str:
    """
    Fix invalid arrow syntax: -->|label|> should be -->|label|
    """
    code = re.sub(r'-->\|([^|]+)\|>', r'-->|\1|', code)
    return code


def _fix_er_diagram_attributes(code: str) -> str:
    """Fix erDiagram attributes that use classDiagram syntax."""
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

        if not in_entity_block:
            fixed_lines.append(line)
            continue

        match1 = re.match(r'^\+?\s*(\w+)\s*:\s*(\w+)\s*(PK|FK)?\s*$', stripped)
        if match1:
            field_name = match1.group(1)
            type_name = match1.group(2)
            key_marker = match1.group(3) or ''
            fixed = f"{type_name} {field_name}"
            if key_marker:
                fixed += f" {key_marker}"
            leading = line[:len(line) - len(line.lstrip())]
            fixed_lines.append(leading + fixed)
            continue

        match2 = re.match(r'^\+\s*(\w+)\s+(\w+)\s*(PK|FK)?\s*$', stripped)
        if match2:
            type_name = match2.group(1)
            field_name = match2.group(2)
            key_marker = match2.group(3) or ''
            fixed = f"{type_name} {field_name}"
            if key_marker:
                fixed += f" {key_marker}"
            leading = line[:len(line) - len(line.lstrip())]
            fixed_lines.append(leading + fixed)
            continue

        fixed_lines.append(line)

    return '\n'.join(fixed_lines)


def _fix_er_relationships(code: str) -> str:
    """Fix erDiagram relationship lines with trailing }."""
    lines = code.split('\n')
    fixed_lines = []

    for line in lines:
        stripped = line.strip()

        if "--" in stripped and ":" in stripped and stripped.endswith("}"):
            if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*\s*\{\s*$', stripped):
                stripped = stripped[:-1].rstrip()
                leading = line[:len(line) - len(line.lstrip())]
                fixed_lines.append(leading + stripped)
                continue

        fixed_lines.append(line)

    return '\n'.join(fixed_lines)