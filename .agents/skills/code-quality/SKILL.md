---
name: code-quality
description: Local code-quality workflow for backend and frontend projects: run safe deterministic auto-fixes before read-only lint/format/type/test checks, expose Makefile fix/check targets, and keep CI verification non-mutating.
---

# Code Quality Standard

Local agent-driven development should normalize changed code before running read-only quality checks.

The goal is to avoid wasting tool calls on predictable formatting and lint failures that can be fixed automatically.

## Core workflow

Preferred local flow:

```text
implementation
  -> safe auto-fix
  -> targeted type/test checks
  -> targeted fixes
  -> make check
  -> optional make verify
```

Do not deliberately run formatting/lint validation first when the configured tools can safely normalize the same code automatically.

## Safe auto-fix phase

Before the normal validation phase, run the project's safe deterministic fix command.

Preferred public interface:

```text
make fix
```

For monorepos, the root target may delegate to component targets:

```text
make fix
  -> backend make fix
  -> frontend make fix
```

The exact implementation depends on the stack.

## Python backend

For Python projects using Ruff, a typical local fix phase may include:

```text
ruff check --fix
ruff format
```

or equivalent project Make targets.

Use safe configured fixes.

Do not enable broad unsafe fixes merely to make checks pass unless the project explicitly allows them.

After auto-fix, run read-only validation such as:

```text
ruff check
ruff format --check
mypy ...
pytest ...
```

## Frontend

For Vue/TypeScript projects, use the configured formatter/linter auto-fix commands before read-only checks.

Typical examples may include:

```text
eslint --fix
prettier --write
```

or the equivalent package scripts.

After auto-fix, run read-only validation such as:

```text
eslint
prettier --check
vue-tsc / tsc
vitest
```

Preserve the package manager and tools already selected by the project.

## Type checking is not an auto-formatter

Do not pretend that `mypy`, `pyright`, `tsc`, or `vue-tsc` has a general reliable auto-fix mode when it does not.

During implementation, proactively write code with correct types and fix obvious typing issues as part of the edit.

After deterministic formatter/linter fixes, run the smallest relevant type check.

If type checking reports errors:

```text
type check
  -> inspect only relevant diagnostics
  -> edit affected code
  -> rerun targeted type check
```

Do not rerun the complete quality pipeline after each type correction.

## Tests are validation, not auto-fix

Tests normally cannot be auto-fixed safely.

Before running tests:

- finish the intended implementation;
- update the required tests;
- run safe formatter/linter auto-fix.

Then run the smallest relevant test target.

If a test fails, fix the underlying code/test and rerun only the affected test first.

## Makefile interface

Projects using Makefiles should prefer a clear separation:

```text
make fix
make check
make verify
make ci
```

Recommended meaning:

### `make fix`

Mutating local normalization.

May include:

- backend formatter;
- backend safe lint auto-fix;
- frontend formatter;
- frontend safe lint auto-fix.

It should not:

- change business behavior intentionally;
- run destructive migrations;
- silently apply unsafe semantic rewrites.

### `make check`

Fast read-only validation.

Typically:

- lint check;
- format check;
- static type check;
- unit tests.

`make check` must not modify tracked source files.

### `make verify`

Broader read-only/local verification when justified.

May include:

- integration tests;
- build validation;
- Docker/Compose checks;
- selected E2E.

### `make ci`

Full CI verification.

It must be suitable for GitHub Actions and should be non-mutating.

## Component Makefiles

When backend and frontend have separate Makefiles, they should expose equivalent concepts where practical.

Example:

```text
backend/
  make fix
  make check

frontend/
  make fix
  make check

root/
  make fix      # delegates to both
  make check    # delegates to both
```

Do not duplicate tool configuration in Makefiles; Make targets should call the project's configured tools/package scripts.

## Changed-scope optimization

During active development, prefer fixing/checking only the affected component when supported.

Examples:

- backend-only change -> backend fix/check;
- frontend-only change -> frontend fix/check;
- full-stack change -> both.

Before final commit, run the project's normal root `make fix` when it is cheap and deterministic, followed by `make check`.

Do not run unrelated expensive suites merely because formatting changed in another component.

## Compact command output

Quality commands should produce the shortest useful output.

Prefer tool options that:

- suppress routine success noise;
- retain errors and diagnostics;
- avoid verbose progress output;
- show concise summaries.

For tests, use compact reporters/output where available.

For type checking, linting, and formatting, avoid verbose/debug output unless required to diagnose a failure.

Make targets should avoid echoing long command banners when that adds no value. Recipes may use quiet Make conventions such as `@` where appropriate.

Do not hide actual diagnostics merely to reduce output.

On failure, increase verbosity only for the failing command and only as much as needed.

## CI must never auto-fix

GitHub Actions is an independent verification layer.

CI should run read-only commands and fail if the repository is not already normalized.

Do not run:

- `ruff check --fix`;
- `ruff format` in write mode;
- `eslint --fix`;
- `prettier --write`;

as the normal CI validation path.

CI should instead use check modes such as:

- `ruff check`;
- `ruff format --check`;
- ESLint without `--fix`;
- `prettier --check`;
- type checking;
- tests.

If CI finds a formatting/lint issue, fix it in the task branch and push the corrected code.

## Plan aggregate checks

Before running local validation, understand what the project's public Make targets include.

Do not execute full suites independently and then immediately execute an aggregate target that reruns the same suites.

Use targeted tests/checks while editing, then let the aggregate target provide the single broad pass.

Example:

```text
changed backend quota tests
-> make fix
-> targeted typecheck / targeted pytest
-> make check
-> make verify only if integration/E2E/infrastructure coverage is required
```

If `make verify` already includes `make check`, run only `make verify` at the final broad stage unless a prior fast check is useful for failure isolation.

Project Makefiles/AGENTS.md should document target coverage clearly enough that Codex does not need to discover it by repeatedly running commands.

## Avoid redundant validation

Bad local flow:

```text
format --check
  -> fails
format/write
  -> format --check
lint
  -> fails on auto-fixable issue
lint --fix
  -> lint
typecheck
tests
```

Preferred local flow:

```text
make fix
  -> targeted typecheck/tests
  -> targeted corrections
  -> make check once
```

This reduces predictable failed checks and unnecessary agent/tool usage.

## Completion criteria

Code-quality work is ready for final validation when:

- safe auto-fixes have been applied;
- changed files are normalized;
- targeted type/tests pass;
- `make check` passes without modifying files;
- broader verification is used only when justified;
- CI can verify the committed state without applying fixes.
