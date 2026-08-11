# Copilot Instructions — AgentDocx SpecKit

## CRITICAL: Task Status Reporting

YOU MUST follow this rule EXACTLY:

### Before implementing ANY task:

1. Read tasks.md to find the task you will implement.
2. Build a full status snapshot of **every** task listed in tasks.md:
   - The task you are about to start → `"in_progress"`
   - Any task whose checkbox is already `[x]` → `"done"`
   - Every other task → `"todo"`
3. WRITE this file IMMEDIATELY at `.task_runtime/current-task.json`:

```json
{
  "task_id": "THE_TASK_ID",
  "file": "THE_FILE_PATH",
  "status": "in_progress",
  "project_name": "PROJECT_NAME",
  "updated_at": "2026-08-10T10:30:00.000000+00:00",
  "tasks": {
    "T001": "done",
    "T002": "done",
    "T003": "in_progress",
    "T004": "todo"
  }
}
```

Example:
```json
{
  "task_id": "T004", 
  "file": "src/routes.py", 
  "status": "in_progress",
  "project_name": "001-cli-todo-manager",
  "updated_at": "2026-08-10T10:30:00.000000+00:00",
  "tasks": {
    "T001": "done",
    "T002": "done",
    "T003": "done",
    "T004": "in_progress",
    "T005": "todo"
  }
}
```

### After completing the task:

1. Mark the task's checkbox as `[x]` in tasks.md.
2. Rebuild the full status snapshot the same way as above — this task now reports `"done"` instead of `"in_progress"`.
3. WRITE this file at `.task_runtime/current-task.json`:

```json
{
  "task_id": "THE_TASK_ID",
  "file": "THE_FILE_PATH",
  "status": "done",
  "project_name": "PROJECT_NAME",
  "updated_at": "2026-08-10T10:45:00.000000+00:00",
  "tasks": {
    "T001": "done",
    "T002": "done",
    "T003": "done",
    "T004": "todo"
  }
}
```

### Why the `tasks` map matters

The backend does **not** read checkboxes in tasks.md to determine ticket status — it only trusts `current-task.json`. If `tasks` is missing, or only lists the task you're currently touching, any task whose transition wasn't caught live (e.g. the backend wasn't running at that moment) will stay stuck in its last known state forever, even though tasks.md shows it as done. Always write the **complete** map, for every task in tasks.md, every single time you write this file — not just the one task you're working on.

### Project Name Guidelines:
- Extract the project name from the specs directory structure: `specs/PROJECT_NAME/tasks.md`
- For example: `specs/001-cli-todo-manager/tasks.md` → `project_name: "001-cli-todo-manager"`
- If working directly in specs/tasks.md, use the parent directory name as project name

### NEVER skip this step. The backend depends on this file to track progress and sync status to the kanban board.