# Plan: Connect Frontend & Backend for Add Document Flow

## Context

The frontend (React/MUI on port 5000) and backend (FastAPI on port 8000) are completely disconnected. The Add Document page simulates uploads with `setTimeout`, and the Documents page uses static mock data. The goal is to enable a real flow: upload a `.md` file, trigger the LangGraph agent pipeline, and display live document status in the Documents table.

## Changes Overview

### 1. Backend: New Upload Endpoint (`backend/app/api/docs.py`)

Add `POST /api/v1/docs/upload` that accepts `multipart/form-data` with:
- `file`: the `.md` file
- `project_name`: string

Flow:
1. Save uploaded file to `test_files/{filename}`
2. Find or create `Project` with the given name
3. Find or create `Artifact` with `source_path` and `artifact_type`
4. Start the LangGraph pipeline in a **background thread** (using `threading.Thread` since the pipeline is synchronous/blocking)
5. Return `{ artifact_id, pipeline_run_id, status: "parsing" }` immediately

The background thread will invoke `create_pipeline_workflow().invoke({"file_name": ..., "file_content": ...})`. The pipeline nodes already handle DB updates (creating PipelineRun, updating KPIs, creating DocVersion on completion).

**Problem**: The pipeline's `_create_pipeline_run()` creates its own Artifact+PipelineRun. To avoid duplication, modify `_create_pipeline_run()` in `backend/app/graph/nodes.py` to look up an existing Artifact by `source_path` before creating a new one.

### 2. Backend: Documents List Endpoint (`backend/app/api/docs.py`)

Add `GET /api/v1/docs/documents` that returns ALL artifacts with their latest pipeline run status (not just completed DocVersions like the existing `/dashboard` endpoint).

Response shape (per row):
```json
{
  "id": "artifact-uuid",
  "name": "constitution",
  "projectName": "Learning Platform",
  "version": "v1",
  "status": "parsing | parallel_enrichment | writing | layout | completed | failed",
  "kpi": 85.6,
  "pipelineRunId": "run-uuid"
}
```

Query: Join `Artifact` -> `Project`, then left-join the latest `PipelineRun` per artifact (via subquery or `order_by + first`).

### 3. Backend: Pipeline Status Endpoint (reuse existing)

The existing `GET /api/v1/docs/pipeline-run/{run_id}` already returns `PipelineRunResponse` with `current_stage` and KPI scores. The frontend will poll this for real-time status updates.

### 4. Backend: Fix CORS (`backend/app/main.py`)

Add `http://localhost:5000` to `allow_origins` (the actual frontend port).

### 5. Frontend: AddDocument Page (`frontend/src/scenes/addDocument/index.jsx`)

Replace the simulated `setTimeout` with a real `fetch` call:

```javascript
const formData = new FormData();
formData.append("file", selectedFile);
formData.append("projectName", values.projectName);

const response = await fetch("http://localhost:8000/api/v1/docs/upload", {
  method: "POST",
  body: formData,
});
```

On success: show success message, optionally navigate to `/documents`.

### 6. Frontend: Documents Page (`frontend/src/scenes/documents/index.jsx`)

Replace `mockDataDocuments` with live data:

1. `useEffect` fetches `GET http://localhost:8000/api/v1/docs/documents` on mount
2. Map backend response to DataGrid row format
3. Add **polling** (every 3 seconds) to refresh data while any document has a non-terminal status (`parsing`, `parallel_enrichment`, `writing`, `layout`)
4. Map `agentEvaluations` from pipeline-run KPI scores (basic mapping for now)
5. "View" button opens/downloads the generated PDF via `GET /api/v1/docs/pdf/{doc_version_id}`
6. `DocumentRow` schema includes `doc_version_id` (nullable, only set when pipeline completes)

## Files to Modify

| File | Change |
|------|--------|
| `backend/app/main.py` | Add `http://localhost:5000` to CORS origins |
| `backend/app/api/docs.py` | Add `/upload` and `/documents` endpoints |
| `backend/app/schema.py` | Add `UploadResponse`, `DocumentRow` schemas |
| `backend/app/graph/nodes.py` | Modify `_create_pipeline_run()` to reuse existing Artifacts |
| `frontend/src/scenes/addDocument/index.jsx` | Replace setTimeout with real fetch to backend |
| `frontend/src/scenes/documents/index.jsx` | Replace mockDataDocuments with API fetch + polling |

## Verification

1. Start backend: `cd backend && python -m uvicorn app.main:app --reload --port 8000`
2. Start frontend: `cd frontend && npm start`
3. Go to Add Document tab, enter project name, select a `.md` file, click "Upload & Process"
4. Verify: file is saved, pipeline starts, API returns 200
5. Go to Documents tab, verify new row appears with "parsing" status
6. Wait and verify status updates: parsing -> parallel_enrichment -> writing -> layout -> completed
7. Verify KPI score appears on completion
8. Click "View" button and verify PDF downloads/opens
