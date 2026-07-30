# Quickstart Validation Guide: Task Management API

This guide provides a set of runnable scenarios to verify that the Task Management API is functioning correctly end-to-end

## Prerequisites

- Python 3.10+ installed
- Project dependencies installed (`pip install -r requirements.txt`)
- API server running (e.g., `uvicorn app.main:app --reload`)

## Validation Scenarios
### Scenario 1: The Happy Path (CRUD Lifecycle)
**Goal**: Verify that a task can be created, read, updated, and deleted.

1. **Create**: `POST /tasks` with `{"title": "Test Task", "description": "Verify CRUD"}`.
   - **Expected**: `201 Created`, response contains a UUID.
2. **Read**: `GET /tasks/{id}` using the UUID from step 1.
   - **Expected**: `200 OK`, response matches the created task.
3. **Update**: `PUT /tasks/{id}` with `{"title": "Updated Title"}`.
   - **Expected**: `200 OK`, title is now "Updated Title".
4. **Delete**: `DELETE /tasks/{id}`.
   - **Expected**: `204 No Content`.
5. **Verify Deletion**: `GET /tasks/{id}`.
   - **Expected**: `404 Not Found`.

### Scenario 2: Status Management & Validation
**Goal**: Verify that task status transitions are handled and validated.

1. **Create**: `POST /tasks` with `{"title": "Status Task"}`.
2. **Complete**: `PUT /tasks/{id}` with `{"status": "completed"}`.
   - **Expected**: `200 OK`, status is now `completed`.
3. **Invalid Status**: `PUT /tasks/{id}` with `{"status": "archived"}`.
   - **Expected**: `400 Bad Request` (or `422 Unprocessable Entity` via Pydantic).

### Scenario 3: Filtering & Listing
**Goal**: Verify that the task list can be filtered by status.

1. **Setup**: Create one "pending" task and one "completed" task.
2. **Filter Pending**: `GET /tasks?status=pending`.
   - **Expected**: `200 OK`, list contains only the pending task.
3. **Filter Completed**: `GET /tasks?status=completed`.
   - **Expected**: `200 OK`, list contains only the completed task.
4. **List All**: `GET /tasks`.
   - **Expected**: `200 OK`, list contains both tasks.

## Tools for Validation
- **Swagger UI**: Accessible at `/docs` for interactive testing.
- **cURL/Postman**: For automated script validation.
- **Pytest**: Run `pytest tests/api/` to execute the automated contract tests.
