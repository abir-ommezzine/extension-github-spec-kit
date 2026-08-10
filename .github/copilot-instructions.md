# Copilot Instructions — AgentDocx SpecKit

## CRITICAL: Task Status Reporting

YOU MUST follow this rule EXACTLY:

### Before implementing ANY task:

1. Read tasks.md to find the task you will implement
2. WRITE this file IMMEDIATELY at `.task_runtime/current-task.json`:

```json
{
  "task_id": "THE_TASK_ID", 
  "file": "THE_FILE_PATH", 
  "status": "in_progress",
  "project_name": "PROJECT_NAME",
  "updated_at": "2026-08-10T10:30:00.000000+00:00"
}
```

Example:
```json
{
  "task_id": "T004", 
  "file": "src/routes.py", 
  "status": "in_progress",
  "project_name": "001-cli-todo-manager",
  "updated_at": "2026-08-10T10:30:00.000000+00:00"
}
```

### After completing the task:

WRITE this file at `.task_runtime/current-task.json`:

```json
{
  "task_id": "THE_TASK_ID", 
  "file": "THE_FILE_PATH", 
  "status": "done",
  "project_name": "PROJECT_NAME",
  "updated_at": "2026-08-10T10:45:00.000000+00:00"
}
```

### Project Name Guidelines:
- Extract the project name from the specs directory structure: `specs/PROJECT_NAME/tasks.md`
- For example: `specs/001-cli-todo-manager/tasks.md` → `project_name: "001-cli-todo-manager"`
- If working directly in specs/tasks.md, use the parent directory name as project name

### NEVER skip this step. The backend depends on this file to track progress and sync status to the kanban board.
