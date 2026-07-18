<!-- Project overview intended for AI assistants to understand and help with development -->
# Spec Kit Extension — Project Overview (for AI)

## Purpose
- Short: This repository implements a small documentation-generation system called "Spec Kit Extension" (AgentDocx API). It parses project specification Markdown, runs an agent pipeline to extract structured data,+ generates summaries/diagrams/glossaries, produces written documentation, and saves PDF versions.

## High-level structure
- Backend: FastAPI application (Python) providing REST endpoints to parse specs and inspect pipeline runs.
- Frontend: Vite + React placeholder UI in `frontend/` (basic starter app).
- Specs: Authoring folder `specs/` with human-written Markdown (e.g. `specs/main/spec.md`).
- Storage: `storage/pdfs/` contains generated PDF outputs.

## Key backend components

- Entry: `backend/app/main.py` — starts FastAPI, creates DB tables, mounts API router, configures CORS, ensures `PDF_STORAGE_DIR` exists.
- Config: `backend/app/config.py` — central settings (env file path in `backend/.env`). Important envs:
  - `DATABASE_URL` (default postgres URL),
  - `OPENAI_API_KEY` (optional),
  - `OPENAI_MODEL` (default "gpt-4o"),
  - `PDF_STORAGE_DIR` (default `./storage/pdfs`).
- Database: `backend/app/database.py` — SQLAlchemy engine and session factory. Uses `DATABASE_URL` from settings.

### ORM models (`backend/app/models.py`)
- `Project`: project container with `artifacts` relationship.
- `Artifact`: represents a authored file (source_path) with `artifact_type` enum (spec, plan, task, constitution, contract, requirements).
- `DocVersion`: stores PDF path, version number, commit hash, and links to `PipelineRun`.
- `PipelineRun`: tracks a pipeline execution for an artifact with `current_stage` enum and step outputs (structured_json, summary_output, diagram_output, glossary_output, written_doc, layout_output), timestamps and error_message.

### Pydantic schemas (`backend/app/schemas.py`)
- Request/response shapes used by the FastAPI endpoints: `ProjectResponse`, `ArtifactResponse`, `DocVersionResponse`, `PipelineRunResponse`, `ParseRequest`, `ParseResponse`.

## Agents and pipeline

- `backend/app/agents/pipeline.py`: Orchestrates pipeline runs. Key function `run_parsing_stage(db, artifact, file_path)`:
  - Creates a `PipelineRun` record with stage `parsing`.
  - Resolves and reads the markdown file (tries absolute path, project root, backend folder).
  - Calls the Parsing Agent (`parse_context_md`) to produce structured JSON.
  - Saves structured JSON to the `PipelineRun` and marks it completed or failed.

- `backend/app/agents/llm_client.py`: Lightweight LLM wrapper.
  - Uses `OPENAI_API_KEY` and `OPENAI_MODEL` from settings.
  - Sends chat completion requests to OpenAI’s `chat/completions` endpoint using `httpx`.
  - Contains a `_mock_response()` helper used when no API key is configured (helpful for tests).

## API routes (important endpoints)
- Router prefix: included under `/api/v1` in `main.py`.
- Documentation endpoints: `backend/app/api/docs.py` (`APIRouter(prefix="/docs")`)
  - `POST /api/v1/docs/parse` — body: `{ "file_path": "specs/main/spec.md" }`. Resolves file path, creates or finds Artifact, runs parsing pipeline, and returns structured JSON and pipeline_run id.
  - `GET /api/v1/docs/pipeline-run/{run_id}` — fetch pipeline run status and outputs.
  - `GET /api/v1/docs/artifact/{artifact_id}/versions` — list PDF versions for an artifact.

## File resolution behavior
- The server resolves requested paths by checking (in order):
 1. as given (absolute or relative to current working directory),
 2. relative to project root (parent of `backend/`),
 3. relative to the `backend/` directory.

## Dependencies
- See `backend/requirements.txt`. Notable packages: `fastapi`, `uvicorn`, `SQLAlchemy`, `pydantic`, `httpx`, `psycopg2` (via `psycopg[binary]`).

## Frontend
- `frontend/` is a Vite + React app. Entry `frontend/src/App.tsx` is currently a starter UI.
- Package manager scripts available in `frontend/package.json`: `dev`, `build`, `preview`.

## How to run locally (development)

Backend (from project root):
```bash
cd backend
# (recommended) create and activate a virtualenv, install requirements
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
# set environment variables in backend/.env (DATABASE_URL, OPENAI_API_KEY optional)
uvicorn app.main:app --reload --port 8000
```

Frontend (from project root):
```bash
cd frontend
npm install
npm run dev
```

API examples:
```bash
# Parse a markdown file (example)
curl -X POST "http://localhost:8000/api/v1/docs/parse" -H "Content-Type: application/json" -d '{"file_path":"specs/main/spec.md"}'
```

## Where to look first when you ask for help
- Parsing logic: `backend/app/agents/parsing_agent.py` (not included in this summary readout — check this file for the parser implementation and prompt engineering).
- Pipeline orchestration and DB interactions: `backend/app/agents/pipeline.py` and `backend/app/api/docs.py`.
- LLM calls and mocks: `backend/app/agents/llm_client.py`.
- DB models and migrations: `backend/app/models.py` and `backend/alembic` (if present).

## Notes for an AI assistant (how you can help)
- Improve parsing prompts and robustness of `parse_context_md`.
- Add retry/backoff and better error handling around LLM calls in `llm_client.py`.
- Extend the pipeline with summary/diagram/glossary workers and unit tests for each agent.
- Add CI checks and tests for `run_parsing_stage` (mock file reads and LLM responses).
- Create minimal frontend pages to call the parse endpoint and show pipeline progress.

## Important files (quick links)
- Project entry: [backend/app/main.py](backend/app/main.py)
- Config: [backend/app/config.py](backend/app/config.py)
- DB models: [backend/app/models.py](backend/app/models.py)
- Pipeline orchestrator: [backend/app/agents/pipeline.py](backend/app/agents/pipeline.py)
- LLM client: [backend/app/agents/llm_client.py](backend/app/agents/llm_client.py)
- API docs router: [backend/app/api/docs.py](backend/app/api/docs.py)
- Specs folder: [specs/main/spec.md](specs/main/spec.md)
- Frontend entry: [frontend/src/App.tsx](frontend/src/App.tsx)

---
If you want, I can now:
- run the backend locally and verify the parse endpoint (requires DB access), or
- generate unit tests and example requests for the parsing pipeline, or
- expand the README with development notes and checklist.
