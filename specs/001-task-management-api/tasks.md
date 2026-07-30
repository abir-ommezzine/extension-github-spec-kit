# Tasks: Task Management REST API

**Input**: Design documents from `/specs/001-task-management-api/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), data-model.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create project structure per implementation plan in `backend/app/`
- [x] T002 Initialize Python project with FastAPI, Pydantic, and Uvicorn dependencies in `requirements.txt`
- [x] T003 [P] Configure linting and formatting tools (ruff/black)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

- [x] T004 Setup SQLite database connection and SQLAlchemy session management in `backend/app/database.py`
- [x] T005 [P] Implement base API routing and middleware structure in `backend/app/main.py`
- [x] T006 [P] Configure environment variables and app settings in `backend/app/core/config.py`
- [x] T007 Implement global error handling and standard API response wrappers in `backend/app/utils/`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Basic Task Lifecycle (Priority: P1) 🎯 MVP

**Goal**: Enable core CRUD operations for tasks.

**Independent Test**: Sequence of POST, GET, PUT, and DELETE requests on `/tasks` verifying persistence.

### Implementation for User Story 1

- [x] T008 [P] [US1] Create Pydantic schemas for Task creation and response in `backend/app/schemas/task.py`
- [x] T009 [P] [US1] Create Task database model in `backend/app/models/task.py`
- [x] T010 [US1] Implement Task CRUD service logic in `backend/app/services/task_service.py`
- [x] T011 [US1] Implement Task CRUD endpoints in `backend/app/api/tasks.py`
- [x] T012 [US1] Integrate Task endpoints into main app in `backend/app/main.py`
- [x] T013 [US1] Implement 404 Not Found handling for non-existent task IDs in `backend/app/api/tasks.py`

**Checkpoint**: User Story 1 is fully functional and testable independently

---

## Phase 4: User Story 2 - Task Status Management (Priority: P2)

**Goal**: Allow users to transition tasks between pending and completed.

**Independent Test**: Update `status` field of an existing task and verify via GET.

### Implementation for User Story 2

- [x] T014 [P] [US2] Define TaskStatus Enum in `backend/app/schemas/task.py`
- [x] T015 [US2] Update Task model to use TaskStatus Enum in `backend/app/models/task.py`
- [x] T016 [US2] Implement status transition logic in `backend/app/services/task_service.py`
- [x] T017 [US2] Add validation for invalid status updates in `backend/app/api/tasks.py` (return 400)

**Checkpoint**: User Stories 1 and 2 are fully functional

---

## Phase 5: User Story 3 - Task Filtering & Listing (Priority: P3)

**Goal**: Provide ability to list all tasks and filter by status.

**Independent Test**: Create tasks with different statuses and call `GET /tasks?status=pending`.

### Implementation for User Story 3

- [ ] T018 [US3] Implement status filtering logic in `backend/app/services/task_service.py`
- [ ] T019 [US3] Update GET `/tasks` endpoint to accept `status` query parameter in `backend/app/api/tasks.py`
- [ ] T020 [US3] Implement empty list response (200 OK) for no tasks in `backend/app/api/tasks.py`

**Checkpoint**: All user stories are independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T021 [P] Implement comprehensive API documentation via Swagger UI in `backend/app/main.py`
- [ ] T022 [P] Add logging for all task operations in `backend/app/services/task_service.py`
- [ ] T023 [P] Perform final code cleanup and type-hinting audit across `backend/app/`
- [ ] T024 Run final validation against `spec.md` acceptance criteria

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Phase 1.
- **User Stories (Phase 3-5)**: Depend on Phase 2.
- **Polish (Phase 6)**: Depends on all User Stories.

### User Story Dependencies

- **US1 (P1)**: No dependencies on other stories.
- **US2 (P2)**: Depends on US1 (needs Task entity).
- **US3 (P3)**: Depends on US1 (needs Task listing).

### Parallel Opportunities

- T003 (Setup)
- T005, T006 (Foundational)
- T008, T009 (US1 Models/Schemas)
- T014 (US2 Enum)
- T021, T022, T023 (Polish)

---

## Implementation Strategy

### MVP First (User Story 1 Only)
1. Complete Phase 1 & 2.
2. Implement US1 (T008-T013).
3. Validate CRUD operations.

### Incremental Delivery
1. Foundation $\rightarrow$ US1 (CRUD) $\rightarrow$ US2 (Status) $\rightarrow$ US3 (Filtering) $\rightarrow$ Polish.
