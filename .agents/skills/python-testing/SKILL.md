---
name: python-testing
description: Python testing conventions for unit, integration, regression, and end-to-end tests using pytest-style tooling. Use when creating, restructuring, or reviewing Python tests, fixtures, mocks, test naming, or test execution commands.
---

# Python Testing Standard

Use tests to verify behavior at the smallest meaningful level.

Prefer deterministic, isolated tests with clear ownership and minimal unnecessary setup.

## Test levels

### Unit

Use unit tests for isolated logic such as:

- application services;
- domain rules;
- pure functions;
- validation logic;
- transformations;
- small components with mocked/fake ports.

Unit tests must not require:

- a real database;
- real external APIs;
- network access;
- Docker;
- unrelated infrastructure.

### Integration

Use integration tests for boundaries such as:

- repositories against a database;
- FastAPI route/application wiring;
- database/session behavior;
- filesystem adapters;
- external adapter integration using controlled test doubles or test services;
- migration/database compatibility where relevant.

Integration tests should exercise real integration behavior, not merely duplicate unit tests with more setup.

### E2E

Use E2E tests only for important complete scenarios.

Examples:

- user-facing request travels through frontend/backend and persistence;
- critical API scenario through the full application stack;
- deployment health scenario.

Do not add E2E tests for every implementation detail.

## Directory structure

Default structure:

```text
tests/
├── unit/
├── integration/
├── e2e/
└── conftest.py
```

Mirror meaningful production areas where useful.

Example:

```text
tests/
├── unit/
│   ├── domain/
│   └── services/
│       └── test_ticket_service_unit.py
├── integration/
│   ├── repositories/
│   │   └── test_department_repository_integration.py
│   └── api/
│       └── test_ticket_api_integration.py
├── e2e/
│   └── test_ticket_processing_e2e.py
└── conftest.py
```

Adapt to the existing repository instead of moving tests without a real benefit.

## File naming

Use explicit test level suffixes:

- `test_<component>_unit.py`
- `test_<component>_integration.py`
- `test_<scenario>_e2e.py`

For a service:

`test_ticket_service_unit.py`

For a repository:

`test_department_repository_integration.py`

For an end-to-end scenario:

`test_ticket_processing_e2e.py`

## Test classes

Group tests for one component in a class when it improves navigation.

Example:

```python
class TestTicketService:
    def test_creates_ticket(self) -> None:
        ...

    def test_rejects_invalid_ticket(self) -> None:
        ...
```

Do not create classes only to add nesting when a module contains a single simple test.

## Fixtures

Place fixtures at the smallest scope that supports reuse.

Recommended rules:

- used only by one test class: keep it with that class when practical;
- used by several tests in one module: define it in the test module;
- used by multiple modules in one test area: use a local `conftest.py`;
- used across the full suite: use `tests/conftest.py`.

Class-local pytest fixtures are acceptable when they truly belong only to that class.

Do not move every fixture into the global `conftest.py`.

## Constants and reusable test data

Use a separate file such as:

`tests/constants.py`

only for genuinely shared constants, IDs, payload fragments, or expected values.

Do not put pytest fixtures in a constants module.

If test data becomes complex, prefer small factories/builders over giant static payloads.

## Arrange, Act, Assert

Tests should make setup, action, and assertion easy to understand.

Use comments for Arrange/Act/Assert only when they improve readability; do not add ceremonial comments to obvious tests.

Prefer one behavior per test.

## Mocking and fakes

Mock or fake boundaries, not internal implementation details.

Good unit-test targets for fakes/mocks:

- repository ports;
- connector ports;
- clock/ID providers;
- other external capabilities.

Avoid mocking private methods merely to force a particular implementation.

Tests should remain valid when internal implementation is refactored without changing behavior.

## Async tests

Use the project's configured async pytest support.

Keep event-loop configuration centralized.

Do not create new loops manually in individual tests unless there is a specific technical need.

## Database tests

Repository tests are integration tests.

Use isolated database state.

Prefer:

- transaction rollback;
- per-test database/schema;
- controlled fixtures;

according to the project's database strategy.

SQLite can be useful for lightweight tests, but do not assume it is behaviorally identical to PostgreSQL.

When behavior depends on PostgreSQL-specific features, types, constraints, locking, transactions, or SQL, include PostgreSQL-backed integration coverage.

## Regression tests

For a bug fix, add a regression test when practical.

Preferred flow:

1. create the smallest test that reproduces the issue;
2. verify the failure when useful;
3. fix the production code;
4. verify the regression test passes.

Keep the regression test after the fix.

## Test independence

A test must not depend on:

- execution order;
- state left by a previous test;
- external production services;
- developer-specific local files.

Tests should be independently runnable.

## Execution

Use compact output for agent-driven local checks.

Recommended pytest form:

`pytest -q --tb=short`

Do not enable verbose test output by default.

If a failing test cannot be diagnosed from the compact traceback, rerun only that test with the minimum additional detail required.

Do not print captured logs/stdout for passing tests unless the task explicitly needs them.

During development, run the narrowest useful target:

- one test node;
- one class;
- one file;
- one test directory.

Do not repeatedly run the full suite while debugging one failure.

## Make targets

When the project uses Makefiles, expose appropriate targets such as:

- `test-unit`;
- `test-integration`;
- `test-e2e` when E2E exists;
- `test`;
- `check`.

The exact commands belong to the project, but successful output should remain compact.

## Coverage

Coverage is a diagnostic tool, not the goal.

Do not add low-value tests solely to reach a number.

Prioritize:

- business-critical behavior;
- edge cases;
- regressions;
- boundary behavior;
- error handling.

## New functionality rule

New or changed application logic is not complete until its necessary tests are added or updated.

Pure documentation, formatting, metadata, or equivalent non-behavioral changes do not require artificial tests.
