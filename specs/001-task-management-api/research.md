# Research: Task Management REST API

## Decisions

### 1. Database Choice: SQLite with SQLAlchemy (Async)
- **Decision**: Use SQLite for the MVP persistence layer, accessed via SQLAlchemy 2.0 with the `aiosqlite` driver.
- **Rationale**: SQLite provides a zero-configuration, file-based database that is perfect for MVPs. SQLAlchemy 2.0 offers a powerful ORM with full async support, allowing for an easy migration to PostgreSQL or MySQL in the future without changing business logic.
- **Alternatives considered**: 
    - In-memory dictionary: Too simple, lacks persistence and query capabilities.
    - MongoDB: Overkill for a simple task model; adds operational complexity.
    - Tortoise ORM: Good async-first ORM, but SQLAlchemy has better industry adoption and tooling.

### 2. API Framework: FastAPI
- **Decision**: Use FastAPI as the web framework.
- **Rationale**: Aligns with the project constitution. Provides native async support, automatic OpenAPI/Swagger documentation, and seamless integration with Pydantic for type safety.
- **Alternatives considered**: 
    - Flask: Synchronous by nature (mostly), requires more boilerplate for validation and docs.
    - Django REST Framework: Too heavy for a simple microservice; slower development cycle for small APIs.

### 3. Task Identification: UUID v4
- **Decision**: Use UUIDs instead of auto-incrementing integers for task IDs.
- **Rationale**: Prevents ID enumeration attacks and makes the API more scalable for distributed systems.
- **Symmetry**: Aligns with FR-002.

### 4. Testing Strategy: Pytest + HTTPX
- **Decision**: Use `pytest` as the test runner and `httpx` for making asynchronous requests to the FastAPI app.
- **Rationale**: `httpx` is the industry standard for testing async Python APIs, providing a similar interface to `requests` but with `async/await` support.

## Resolved Clarifications

- **Persistence**: Confirmed SQLite for MVP.
- **Authentication**: Confirmed out of scope for this phase.
- **Concurrency**: Handled by FastAPI's event loop and async DB drivers.
