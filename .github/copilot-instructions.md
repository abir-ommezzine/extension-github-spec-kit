# Copilot Instructions — AgentDocx SpecKit

## CRITICAL: Task Status Reporting

YOU MUST follow this rule EXACTLY:

### Before implementing ANY task:

1. Read tasks.md to find the task you will implement
2. WRITE this file IMMEDIATELY at `.task_runtime/current-task.json`:

```json
{"task_id": "THE_TASK_ID", "file": "THE_FILE_PATH", "status": "in_progress"}
```

Example:
```json
{"task_id": "T004", "file": "src/routes.py", "status": "in_progress"}
```

### After completing the task:

WRITE this file at `.task_runtime/current-task.json`:

```json
{"task_id": "THE_TASK_ID", "file": "THE_FILE_PATH", "status": "done"}
```

### NEVER skip this step. The backend depends on this file to track progress.
