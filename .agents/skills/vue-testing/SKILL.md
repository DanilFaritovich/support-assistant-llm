---
name: vue-testing
description: Vue and TypeScript testing conventions for unit, component, integration, and E2E tests with compact agent-friendly execution. Use when creating, restructuring, or reviewing frontend tests.
---

# Vue Testing Standard

Test frontend behavior at the smallest useful level.

Prefer fast component/unit tests for local behavior and reserve E2E for important user journeys.

## Test levels

### Unit

Use for:

- pure utilities;
- composables with isolated behavior;
- formatting/transformation helpers;
- state logic that does not require full component rendering.

### Component

Use for:

- rendering;
- props;
- emitted events;
- user interactions;
- conditional UI;
- loading/error states.

Use the project's configured Vue testing tooling, typically Vitest and Vue Test Utils when available.

### Integration

Use when behavior spans meaningful frontend boundaries, for example:

- view + composable + mocked API layer;
- router integration;
- shared state + components;
- form behavior with API client interaction.

Mock the transport boundary rather than internal component implementation details.

### E2E

Use E2E only for important complete user workflows.

Examples:

- user opens a page, submits data, and sees the backend result;
- authentication flow;
- critical create/update flow;
- deployment smoke scenario.

Do not create E2E tests for every component.

## Suggested structure

Adapt to the existing project, but prefer an explicit structure such as:

```text
tests/
├── unit/
├── integration/
└── e2e/
```

or colocated unit/component tests plus a separate `e2e/` directory when that matches the project's tooling.

Be consistent within one repository.

## Naming

Use descriptive names tied to behavior.

When central test directories are used, prefer explicit suffixes where helpful:

- `<component>.unit.spec.ts`
- `<feature>.integration.spec.ts`
- `<scenario>.e2e.spec.ts`

If the existing frontend uses `.test.ts` or another convention, preserve it consistently.

## API mocking

Frontend unit/component tests should not call production APIs.

Mock at the API client / HTTP boundary.

Do not mock private component methods simply to force implementation details.

Tests should survive internal refactoring when observable behavior is unchanged.

## Fixtures and test data

Keep test data close to the tests that use it.

Promote shared builders/fixtures only when they are genuinely reused.

Avoid large global fixture files that make tests hard to understand.

## Assertions

Assert user-visible or contract-relevant behavior.

Prefer:

- rendered content;
- emitted events;
- API calls at the boundary;
- route changes;
- meaningful state changes.

Avoid asserting framework internals without a specific reason.

## E2E data

E2E tests should use deterministic test data and isolated environments.

Do not depend on production accounts or mutable external state.

## Compact execution

Agent-driven local validation should use the configured test runner's compact/silent reporter when it preserves useful failure diagnostics.

Do not use verbose reporters by default.

For a failure, rerun only the affected test/spec with additional detail when the compact output is insufficient.

Avoid printing browser traces, screenshots, full console logs, or large snapshots unless they are needed to diagnose the current failure.

During development, run:

- one test;
- one spec file;
- one relevant directory;

before running the broader frontend check.

Do not repeatedly run the entire frontend suite while debugging one failing test.

## CI

GitHub CI may run:

- full unit/component suite;
- integration suite;
- selected E2E;
- frontend build;
- lint and typecheck.

Keep expensive browser-based E2E out of the normal local debugging loop unless needed to reproduce a failure.
