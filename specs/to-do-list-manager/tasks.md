# Tasks: CLI To-Do List Manager

**Input**: Design documents from `/specs/001-cli-todo-manager/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/commands.md

**Tests**: No dedicated test tasks are included because tests were not explicitly requested in the feature spec. Validation is handled through quickstart verification in the polish phase.

**Organization**: Tasks are grouped by user story to keep each story independently implementable and testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and base package structure

- [X] T001 Create the Python package skeleton in `src/todo_manager/__init__.py`, `src/todo_manager/__main__.py`, `src/todo_manager/cli.py`, `src/todo_manager/models.py`, `src/todo_manager/storage.py`, and `src/todo_manager/service.py`
- [ ] T002 Create the test directory structure in `tests/unit/` and `tests/integration/` and add package markers if needed
- [ ] T003 [P] Add project metadata and tooling entry points in `pyproject.toml` for the CLI, test runner, and lint configuration

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared infrastructure that every user story depends on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Implement task entity definitions and serialization helpers in `src/todo_manager/models.py`
- [ ] T005 Implement JSON storage path resolution and file I/O helpers in `src/todo_manager/storage.py`
- [ ] T006 [P] Implement shared command-line parsing and top-level dispatch in `src/todo_manager/cli.py`
- [ ] T007 Implement shared service-layer error handling and task collection utilities in `src/todo_manager/service.py`
- [ ] T008 Define module entry behavior for `python -m todo_manager` in `src/todo_manager/__main__.py`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Add and Manage Tasks (Priority: P1) 🎯 MVP

**Goal**: Let a user create tasks and mark existing tasks as completed from the CLI.

**Independent Test**: Run `todo add "Task description"` and `todo complete <id>`, then confirm the stored task list reflects the new task and its completion status.

### Implementation for User Story 1

- [ ] T009 [US1] Implement the `add` command flow in `src/todo_manager/cli.py` and `src/todo_manager/service.py`
- [ ] T010 [US1] Implement task creation, sequential ID assignment, and `created_at` population in `src/todo_manager/models.py`
- [ ] T011 [US1] Implement completion updates for existing tasks in `src/todo_manager/service.py`
- [ ] T012 [US1] Add user-facing success and error messages for add and complete operations in `src/todo_manager/cli.py`

**Checkpoint**: User Story 1 should now support adding and completing tasks independently.

---

## Phase 4: User Story 2 - View and Filter Tasks (Priority: P2)

**Goal**: Let a user list tasks in readable form or as JSON for scripting.

**Independent Test**: Run `todo list` and `todo list --json` and confirm the output is readable or parseable JSON while showing the full task collection.

### Implementation for User Story 2

- [ ] T013 [US2] Implement human-readable task listing output in `src/todo_manager/cli.py`
- [ ] T014 [US2] Implement `--json` output formatting in `src/todo_manager/cli.py` using the task serialization helpers in `src/todo_manager/models.py`
- [ ] T015 [US2] Add listing logic that preserves task order and status fields in `src/todo_manager/service.py`
- [ ] T016 [US2] Handle the empty-list case with a clear message in `src/todo_manager/cli.py`

**Checkpoint**: User Story 2 should now display tasks correctly in both human-readable and JSON forms.

---

## Phase 5: User Story 3 - Remove and Clear Tasks (Priority: P3)

**Goal**: Let a user remove a single task or clear all completed tasks.

**Independent Test**: Run `todo remove <id>` and `todo clear`, then confirm the targeted task or completed tasks are removed while other tasks remain intact.

### Implementation for User Story 3

- [ ] T017 [US3] Implement the `remove` command flow in `src/todo_manager/cli.py` and `src/todo_manager/service.py`
- [ ] T018 [US3] Implement the `clear` command flow for removing completed tasks in `src/todo_manager/service.py`
- [ ] T019 [US3] Add not-found handling for invalid task IDs in `src/todo_manager/cli.py`
- [ ] T020 [US3] Ensure storage writes persist removals and clears safely in `src/todo_manager/storage.py`

**Checkpoint**: All user stories should now be independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final cleanup and validation across all stories

- [ ] T021 [P] Document the CLI usage and storage behavior in `README.md`
- [ ] T022 [P] Add quickstart verification notes and examples in `specs/001-cli-todo-manager/quickstart.md`
- [ ] T023 Run a manual smoke test of `add`, `list`, `complete`, `remove`, and `clear` against `~/.todos.json`
- [ ] T024 Verify linting and formatting expectations for the source files in `src/todo_manager/`
- [ ] T025 Confirm the generated JSON output remains parseable for the `todo list --json` path

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - blocks all user stories
- **User Stories (Phase 3+)**: Depend on Foundational phase completion
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational - no dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational - may reuse shared task helpers but remains independently testable
- **User Story 3 (P3)**: Can start after Foundational - may reuse shared storage and service code but remains independently testable

### Within Each User Story

- Shared helpers before story-specific CLI wiring
- Service logic before output formatting
- Storage interactions before final error handling
- Story complete before moving to the next priority

### Parallel Opportunities

- `T003` can run in parallel with other setup work
- `T006` can run in parallel with the other foundational tasks because it touches a different file
- `T009` to `T012` can be split across files if implementation is staffed in parallel
- `T013` to `T016` can be parallelized across CLI formatting and service-layer work
- `T017` to `T020` can be parallelized across CLI, service, and storage updates

---

## Parallel Example: User Story 1

```bash
Task: "Implement the `add` command flow in `src/todo_manager/cli.py` and `src/todo_manager/service.py`"
Task: "Implement task creation, sequential ID assignment, and `created_at` population in `src/todo_manager/models.py`"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Stop and validate add/complete behavior against `~/.todos.json`

### Incremental Delivery

1. Complete Setup + Foundational
2. Add User Story 1 and validate it independently
3. Add User Story 2 and validate list output independently
4. Add User Story 3 and validate removal/clear behavior independently
5. Finish with polish and smoke tests

### Parallel Team Strategy

1. Team completes Setup and Foundational together
2. After foundational work is complete:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3
3. Merge and validate each story independently before moving to polish
