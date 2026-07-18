import json
import traceback
from datetime import datetime
from pathlib import Path
from app.agents.llm_client import llm_client

# Log file for parsing errors
_LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)
_LOG_FILE = _LOG_DIR / "parsing_errors.log"


SYSTEM_PROMPT = """You are a document parsing agent.
Analyze the markdown document provided by the user and extract its structure intelligently.

Rules:
1. Auto-detect the document type. Use a descriptive, free-form name (e.g. "Software Requirements Specification", "API Design Document", "Project Plan", "Architecture Decision Record", "Technical Specification", "User Guide", etc.). Do NOT force it into a rigid category.
2. Extract the document title if present.
3. Extract all structured elements naturally found in the text: requirements, tasks, user stories, acceptance criteria, entities, decisions, definitions, constraints, assumptions, milestones, etc. Preserve original identifiers (e.g. REQ-001, US-12) exactly as written.
4. Capture relationships between elements only if explicitly stated or strongly implied by the text. Do not invent relationships.
5. Do not hallucinate information not present in the document.

Return ONLY valid JSON using this exact structure:
{
  "document_type": "<free-form descriptive type>",
  "title": "<document title or null>",
  "summary": "<1-3 sentence summary>",
  "elements": [
    {
      "type": "<natural element type: requirement|task|user_story|acceptance_criterion|entity|decision|definition|constraint|assumption|milestone|section|...>",
      "identifier": "<original ID or null>",
      "content": "<full text of the element>",
      "attributes": {<any additional key-value metadata found in the doc, e.g. priority, status, author>}
    }
  ],
  "relationships": [
    {"from": "<identifier or short content>", "to": "<identifier or short content>", "relation_type": "<depends_on|implements|contains|relates_to|...>"}
  ]
}
"""


def _extract_json(raw: str) -> dict:
    """Pull JSON out of an LLM response that may be wrapped in markdown."""
    text = raw.strip()

    # Try fenced code block
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0].strip()
    elif text.startswith("```"):
        text = text.split("```", 1)[1].split("```", 1)[0].strip()
    # Try direct JSON parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Fallback: attempt to find the first JSON object in the text by locating
        # the first '{' and the last '}' and parsing that substring.
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            candidate = text[start:end+1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass

    # If nothing worked, raise so the caller can include raw output in the error message.
    raise json.JSONDecodeError("Could not extract valid JSON from LLM response", raw, 0)


def _fallback_parse_markdown(content: str, source_path: str | None = None) -> dict:
    """Heuristic fallback parser for markdown when LLM output is invalid.

    This produces a conservative JSON envelope so downstream code can continue.
    """
    import re
    lines = content.splitlines()

    # Title: first H1 or H2
    title = None
    for ln in lines:
        m = re.match(r"^#\s+(.*)", ln)
        if m:
            title = m.group(1).strip()
            break

    # Summary: first non-empty paragraph (not a heading)
    summary = ""
    para = []
    for ln in lines:
        if ln.strip() == "" and para:
            break
        if not ln.strip().startswith("#"):
            para.append(ln)
    if para:
        summary = " ".join([p.strip() for p in para]).strip()
        # trim to 300 chars
        if len(summary) > 300:
            summary = summary[:297] + "..."

    # Elements: each H2/H3 becomes a section element
    elements = []
    current_section = None
    buffer = []
    for ln in lines:
        h = re.match(r"^(##+)\s+(.*)", ln)
        if h:
            if current_section:
                elements.append({
                    "type": "section",
                    "identifier": None,
                    "content": "\n".join(buffer).strip(),
                    "attributes": {"heading": current_section},
                })
            current_section = h.group(2).strip()
            buffer = []
            continue
        if current_section:
            buffer.append(ln)

    if current_section and buffer:
        elements.append({
            "type": "section",
            "identifier": None,
            "content": "\n".join(buffer).strip(),
            "attributes": {"heading": current_section},
        })

    # Heuristic document type from filename
    doc_type = "unknown"
    if source_path:
        sp = source_path.lower()
        if "contract" in sp:
            doc_type = "contract"
        elif "constitution" in sp:
            doc_type = "constitution"
        elif "plan" in sp:
            doc_type = "project plan"
        elif "requirements" in sp:
            doc_type = "requirements"
        elif "spec" in sp:
            doc_type = "specification"

    return {
        "document_type": doc_type,
        "title": title,
        "summary": summary,
        "elements": elements,
        "relationships": [],
    }


async def parse_context_md(content: str, source_path: str | None = None) -> dict:
    """
    Parse markdown content using an LLM.
    The LLM auto-detects the document type and extracts a flexible structure.
    Raises on LLM failure or invalid JSON — no silent fallback, no mock data.
    """
    user_prompt = f"Parse this document"
    if source_path:
        user_prompt += f" (source: {source_path})"
    user_prompt += f":\n\n{content}"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Parse this document{f' (source: {source_path})' if source_path else ''}:\n\n{content}"},
    ]

    try:
        raw_response = await llm_client.chat_completion(messages)
    except Exception as exc:
        try:
            with _LOG_FILE.open("a", encoding="utf-8") as fh:
                fh.write("\n--- LLM CLIENT ERROR ---\n")
                fh.write(f"timestamp: {datetime.utcnow().isoformat()}Z\n")
                fh.write(f"source_path: {source_path}\n")
                fh.write(f"exception: {exc}\n")
                fh.write(traceback.format_exc())
                fh.write("\n--- ORIGINAL CONTENT START ---\n")
                fh.write(content[:10000])
                fh.write("\n--- ORIGINAL CONTENT END ---\n")
        except Exception:
            pass
        raise RuntimeError(f"LLM client error: {exc}") from exc

    try:
        parsed = _extract_json(raw_response)
    except json.JSONDecodeError:
        # Use a conservative local markdown parser as a fallback so we don't return 500
        parsed = _fallback_parse_markdown(content, source_path)
        # Annotate that a fallback was used
        parsed.setdefault("_fallback_used", True)
        parsed.setdefault("_llm_raw", raw_response[:1000])

    if not isinstance(parsed, dict):
        try:
            with _LOG_FILE.open("a", encoding="utf-8") as fh:
                fh.write("\n--- PARSING ERROR ---\n")
                fh.write(f"timestamp: {datetime.utcnow().isoformat()}Z\n")
                fh.write(f"source_path: {source_path}\n")
                fh.write("exception: LLM response JSON is not an object\n")
                fh.write("--- RAW LLM RESPONSE START ---\n")
                fh.write(raw_response[:10000])
                fh.write("\n--- RAW LLM RESPONSE END ---\n")
                fh.write("--- ORIGINAL CONTENT START ---\n")
                fh.write(content[:10000])
                fh.write("\n--- ORIGINAL CONTENT END ---\n")
        except Exception:
            pass
        raise ValueError("LLM response JSON is not an object")

    # Ensure minimal envelope so downstream agents don't crash on missing keys
    parsed.setdefault("document_type", "unknown")
    parsed.setdefault("title", None)
    parsed.setdefault("summary", "")
    parsed.setdefault("elements", [])
    parsed.setdefault("relationships", [])

    return parsed