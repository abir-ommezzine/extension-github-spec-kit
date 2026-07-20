# Spec Kit Extension — Diagram Agent (AI-facing)

## Project overview

This repository implements a Spec Kit extension that parses project specifications and generates artifacts (including diagrams) to help engineers and product teams. The codebase contains a Python backend (FastAPI) under `backend/` and a TypeScript frontend under `frontend/`.

Key backend folders:

- `backend/app/agents/` — contains agents (LLM clients, parsing, diagram generation).
- `backend/app/main.py` — FastAPI app entrypoint.
- `backend/app/models.py`, `schemas.py` — domain models and Pydantic schemas.

The goal of this document is to describe the **Diagram Agent** precisely so you can hand it to another AI to help implement, refactor, or extend it.

---

## Diagram Agent — Purpose

The Diagram Agent analyzes a structured (parsed) representation of a document (requirements, user flows, data models, etc.) and returns 1–4 Mermaid diagrams describing the important concepts, flows, or relationships.

Primary responsibilities:

- Accept a structured JSON representing parsed spec content.
- Compose a deterministic prompt and call the LLM chat API.
- Parse the LLM response (expected to be JSON containing diagrams).
- Validate diagram types against a whitelist and sanitize the output.
- Return a normalized `{"diagrams": [...]}` object ready for storage or rendering.

---

## Existing implementation notes

See current implementation: `backend/app/agents/diagram_agent.py`.

Important symbols:

- `SYSTEM_PROMPT` — the system instructions sent to the LLM; dictates allowed diagram types and JSON output format.
- `_extract_json(raw: str) -> dict` — helper that strips Markdown code fences and parses JSON.
- `generate_diagrams(structured_json: dict) -> dict` — async function that calls `llm_client.chat_completion(...)`, extracts JSON, filters to allowed types, and returns normalized diagrams.
- `ALLOWED_TYPES` — whitelist of mermaid diagram types the agent accepts: `flowchart`, `sequenceDiagram`, `classDiagram`, `erDiagram`, `stateDiagram`, `gantt`, `mindmap`, `pie`.
- Dependency: `app.agents.llm_client.llm_client` with interface `chat_completion(messages, temperature)` and exception `LLMClientError`.

---

## API / Function contract for AI to implement or extend

- Input: `structured_json` (dict) — a parsed representation of a document. Example minimal shape:

  {
    "title": "Create course management",
    "sections": [
      {"id": "FR-001", "type": "requirement", "text": "Create courses"},
      {"id": "US-1", "type": "user_story", "text": "Instructor creates course"},
      {"id": "model", "entities": [ ... ] }
    ]
  }

- Output: `{"diagrams": [ {"title": str, "type": str, "description": str, "mermaid_code": str}, ... ]}`
  - `type` must be one of the whitelist.
  - `mermaid_code` must be raw Mermaid syntax (no markdown fences).

- Errors:
  - If LLM returns invalid JSON -> raise `ValueError` with helpful diagnostic including raw response start.
  - If LLM client fails -> propagate or wrap `LLMClientError`.
  - If parsed output is not an object -> raise `ValueError`.

---

## Prompt engineering guidance (for the AI that will call an LLM)

- Use the `SYSTEM_PROMPT` style provided in the current implementation: be prescriptive about allowed diagram types and JSON-only responses.
- Keep temperature low (e.g., 0.1) to favor deterministic outputs.
- Ask the LLM to generate 1–4 diagrams, and prefer quality over quantity.
- Provide an example of a traceability flowchart in the system prompt to anchor outputs.

Example messages array to the LLM:

- system: `SYSTEM_PROMPT` (full content from `diagram_agent.py`)
- user: `Generate diagrams for this parsed document:\n\n{structured_json_as_pretty_json}`

---

## Validation & Sanitization rules for the agent

- Accept only diagrams whose `type` is in `ALLOWED_TYPES`.
- Ensure `mermaid_code` is a string and does not include Markdown fences (strip if present).
- Normalize missing `title` to `Diagram N`.
- Limit the returned list to at most 4 diagrams.
- If no useful diagrams are found, return `{"diagrams": []}` (not an error).

---

## Example inputs and expected outputs

Input (short example):

{
  "title": "Course feature",
  "sections": [
    {"id":"FR-001","type":"requirement","text":"Create courses"},
    {"id":"FR-002","type":"requirement","text":"Associate instructor"},
    {"id":"US-1","type":"user_story","text":"Instructor creates course"}
  ]
}

Expected output (one flowchart diagram):

{
  "diagrams": [
    {
      "title": "Requirements -> User Stories",
      "type": "flowchart",
      "description": "Traceability from requirements to user stories",
      "mermaid_code": "flowchart TD\n  subgraph Requirements\n    FR1[FR-001: Create courses]\n    FR2[FR-002: Associate instructor]\n  end\n  subgraph UserStories\n    US1[US-1: Instructor creates course]\n  end\n  FR1 -->|implements| US1"
    }
  ]
}

---

## Unit tests to ask the AI to generate

- Test `_extract_json`:
  - Input raw strings with triple-backtick fences and without; ensure correct JSON extraction and parsing.
  - Malformed JSON returns `json.JSONDecodeError` which `generate_diagrams` wraps into `ValueError`.

- Test `generate_diagrams` happy path (mock `llm_client.chat_completion` to return a valid JSON-within-text string).

- Test `generate_diagrams` filters out disallowed types (mock an LLM response containing `"type": "unsupportedDiagram"`).

- Test LLM error propagation (mock `llm_client.chat_completion` to raise `LLMClientError`).

Suggested test frameworks: `pytest` with `pytest-asyncio` and `pytest-mock` for mocking async functions.

---

## Integration points

- LLM client: `backend/app/agents/llm_client.py` — ensure the client provides an async `chat_completion(messages, temperature)` and raises `LLMClientError` for failures.
- Parsing agent: `backend/app/agents/parsing_agent.py` — produces `structured_json` that becomes the input.
- API layer: add endpoints in `backend/app/api/` to trigger diagram generation and return diagrams JSON for the frontend to render.

---

## Implementation tasks for AI (priority ordered)

1. Make `_extract_json` stricter: remove non-JSON leading/trailing text robustly and return clear errors.
2. Add unit tests covering extraction, filtering, and error cases.
3. Add input validation for `structured_json` shape with helpful error messages.
4. Add instrumentation/logging to capture raw LLM outputs for debugging (redact secrets).
5. Optionally: add a fallback mode that attempts to repair near-JSON outputs (best-effort) and logs a repair note.

---

## Constraints, security & safety

- Do not include secrets or API keys in prompts or logs.
- Sanitize/escape any user-provided text before embedding in prompts to avoid prompt injection.
- Rate-limit and backoff when calling LLMs from production endpoints.

---

## How to use this spec with an AI assistant

Provide this file to the AI and ask it to:

- Implement missing tests and run them locally.
- Harden `_extract_json` and `generate_diagrams` per the tasks above.
- Add an example FastAPI endpoint to call the agent and return diagrams.

---

## File references

- Implementation: backend/app/agents/diagram_agent.py
- LLM client: backend/app/agents/llm_client.py
- Parsing input source: backend/app/agents/parsing_agent.py


---

If you want, I can also:
- Generate the unit tests (`pytest`) for these behaviors.
- Implement an example FastAPI endpoint that uses the diagram agent.

