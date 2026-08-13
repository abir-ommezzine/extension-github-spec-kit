# Copilot Instructions — AgentDocx SpecKit

## CRITICAL: Task Status Reporting

YOU MUST follow this rule EXACTLY:

### ⚠️ There are always TWO writes per task — never skip the first one

For **every single task**, no matter how small or fast: write `.task_runtime/current-task.json` **twice** —
1. Once with `"in_progress"`, immediately **before** you touch any code for that task.
2. Once with `"done"`, immediately **after** you finish it.

Do not skip step 1 "because the task is quick" or do both writes back-to-back at the end. The board is meant to visibly show a task moving from To Do → In Progress → Done — going straight from To Do to Done means step 1 never happened, and that's a bug in your process, not a shortcut.

### ⚠️ NEVER check a task's checkbox before it is 100% finished

A task's checkbox in tasks.md (`[x]`) is the **only** signal this system trusts to mark a task `"done"` on the Kanban board — a human will see `"done"` and believe it, without re-checking your work.

- **Moving on to the next task does NOT mean the previous one is done.** Do not check task N's box just because you're about to start task N+1.
- Only check a box once the task's code is written, saved, and — if the task itself calls for it — actually verified (ran, tested, or manually confirmed working).
- If a task is partially done, blocked, or you're setting it aside to work on something else, **leave its checkbox unchecked**. It will correctly show as `"todo"` in the snapshot below — that's the accurate state, not a bug.
- When in doubt, leave it unchecked. A task incorrectly stuck on `"todo"` is a minor inconvenience; a task incorrectly marked `"done"` is a false report that hides real unfinished work.

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

1. Mark the task's checkbox as `[x]` in tasks.md — **only do this now, when the task is genuinely finished. Never earlier.**
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