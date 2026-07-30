# API Contract: Task Management

**Base URL**: `/api/v1`

## Endpoints

### 1. Create Task
- **Endpoint**: `POST /tasks`
- **Description**: Creates a new task.
- **Request Body**:
  ```json
  {
    "title": "string (required)",
    "description": "string (optional)"
  }
  ```
- **Responses**:
    - `201 Created`: Task created successfully. Returns the created Task object.
    - `422 Unprocessable Entity`: Validation error (e.g., missing title).

### 2. List Tasks
- **Endpoint**: `GET /tasks`
- **Description**: Retrieves a list of all tasks.
- **Query Parameters**:
    - `status` (optional): Filter tasks by status (`pending` or `completed`).
- **Responses**:
    - `200 OK`: List of Task objects.
    - `400 Bad Request`: Invalid status filter provided.

### 3. Get Task by ID
- **Endpoint**: `GET /tasks/{id}`
- **Description**: Retrieves a specific task by its UUID.
- **Responses**:
    - `200 OK`: The requested Task object.
    - `404 Not Found`: Task with the given ID does not exist.

### 4. Update Task
- **Endpoint**: `PUT /tasks/{id}`
- **Description**: Updates an existing task.
- **Request Body**:
  ```json
  {
    "title": "string (optional)",
    "description": "string (optional)",
    "status": "string (optional: pending|completed)"
  }
  ```
- **Responses**:
    - `200 OK`: Task updated successfully. Returns the updated Task object.
    - `400 Bad Request`: Invalid status value provided.
    - `404 Not Found`: Task with the given ID does not exist.

### 5. Delete Task
- **Endpoint**: `DELETE /tasks/{id}`
- **Description**: Removes a task from the system.
- **Responses**:
    - `204 No Content`: Task deleted successfully.
    - `404 Not Found`: Task with the given ID does not exist.

## Data Schemas

### Task Object
```json
{
  "id": "UUID",
  "title": "string",
  "description": "string | null",
  "status": "pending | completed",
  "created_at": "ISO8601 DateTime",
  "updated_at": "ISO8601 DateTime"
}
```
