# Data Model: Task Management REST API

## Entities

### Task
The core entity representing a unit of work.

| Field | Type | Required | Description | Validation Rules |
| :--- | :--- | :--- | :--- | :--- |
| `id` | UUID | Yes | Unique identifier for the task | Must be a valid UUID v4 |
| `title` | String | Yes | Short summary of the task | Max 255 chars, cannot be empty/whitespace |
| `description` | String | No | Detailed explanation of the task | Max 2000 chars |
| `status` | Enum | Yes | Current state of the task | Must be one of: `pending`, `completed` |
| `created_at` | DateTime | Yes | Timestamp of creation | System generated, UTC |
| `updated_at` | DateTime | Yes | Timestamp of last update | System generated, UTC |

## Relationships

- **Self-contained**: The `Task` entity is currently standalone. No relationships to Users or Categories in this MVP scope.

## State Transitions

The `status` field follows a simple transition model:
- `pending` $\rightarrow$ `completed`
- `completed` $\rightarrow$ `pending`

Any attempt to set the status to a value outside the defined Enum will result in a validation error (400 Bad Request).
