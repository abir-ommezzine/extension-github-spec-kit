<!--
Sync Impact Report:
- Version change: 1.5.0 -> 1.0.0
- Modified principles: Total replacement of MediReserve principles with Expense Tracker principles.
- Added sections: Technical Constraints, Development Workflow.
- Removed sections: All MediReserve specific governance and principles.
- Templates requiring updates:
  - .specify/templates/plan-template.md ✅ (no change needed)
  - .specify/templates/spec-template.md ✅ (no change needed)
  - .specify/templates/tasks-template.md ✅ (no change needed)
- Follow-up TODOs: None.
-->

# Expense Tracker Constitution

## Core Principles

### Simplicity and YAGNI (You Ain't Gonna Need It)
Features MUST be implemented only when there is a direct requirement. Avoid abstract base classes or complex patterns unless the logic requires it. Start simple and evolve based on proven needs.

### Data Integrity and Persistence
All data modifications MUST be performed using transactions to ensure atomicity. Data must be persisted in a structured format (e.g., SQLite) to prevent data loss. Invalid data state MUST be prevented via validation at the service layer.

### Modular Architecture (Separation of Concerns)
The project MUST separate data access logic (Repository pattern) from business logic (Services) and the user interface (CLI/API). No UI or presentation code is permitted in the data or service layers.

### TDD for CRUD Operations
Every Create, Read, Update, and Delete operation MUST have an accompanying unit test that verifies the successful operation and handles edge cases (e.g., item not found, validation errors). Tests MUST be written before the implementation code.

### Exhaustive Specification
Every feature MUST be documented in `.specify/specs/` before implementation. This includes both functional requirements (user stories, acceptance criteria) and technical design (data models, API contracts).

## Technical Constraints

The implementation must respect the following technological choices:
- **Language**: Python 3.10+
- **Storage**: SQLite for local persistence.
- **Testing**: `pytest` for all test suites.
- **Interface**: Simple Command Line Interface (CLI).

## Development Workflow

The workflow follows these rules:
1. **Spec First**: Define the requirement and design in `.specify/specs/`.
2. **Test First**: Write a failing test for the specific CRUD operation in `tests/`.
3. **Implement**: Write the minimum code required to make the test pass.
4. **Verify**: Run the full test suite to ensure no regressions.
5. **Document**: Ensure the README and function docstrings are updated.

## Governance

This constitution is the Single Source of Truth for the Expense Tracker project. It supersedes all other development practices. Any modification to these principles requires a version bump, documentation of the changes, and validation by the project lead.

**Version**: 1.0.0 | **Ratified**: 2026-07-24 | **Last Amended**: 2026-07-24
