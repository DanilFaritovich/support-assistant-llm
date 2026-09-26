---
name: task-development-workflow
description: Standard workflow for implementing one software development task with Codex, from branch creation and scoped context loading through implementation, targeted validation, documentation, commit, push, Pull Request, and CI. Use for normal feature, fix, refactor, chore, and documentation tasks.
---

# Task Development Workflow

Use this workflow for a single development task unless the target repository defines stricter project-specific rules.

## Goals

- Implement the complete requested scope.
- Read only the context required for the task.
- Keep unrelated changes out of the task.
- Add or update tests when behavior changes.
- Prefer targeted validation during development.
- Avoid repeated full checks and repeated file reads.
- Use CI as the final independent verification.
- Never merge automatically.

## 1. Start from the development branch

Use the repository's configured development branch. If the project follows the standard profile, this is `develop`.

Before editing:

1. Check the current branch.
2. Check the working tree.
3. Preserve unrelated user changes and untracked files.
4. Create a dedicated task branch from the current development branch.

Recommended prefixes:

- `feature/`
- `fix/`
- `refactor/`
- `chore/`
- `docs/`

Do not perform normal development directly in `develop` or `main`.

## 2. Load only relevant context

Read the applicable `AGENTS.md` first.

Use it as the repository map and source of project-specific rules.

Then determine the task scope and inspect only relevant:

- source files;
- tests;
- interfaces;
- configuration;
- similar implementations;
- documentation when required.

Do not reread the entire repository for every task.

Read `ARCHITECTURE.md` when the task affects architecture, module boundaries, persistence design, service communication, infrastructure, deployment, or external integrations.

Preferred flow:

`AGENTS.md -> determine scope -> search for relevant symbols/paths -> read only relevant ranges`

## Context-efficient repository inspection

Search before reading large files.

Prefer symbol/pattern discovery such as:

```text
rg -n "RelevantClass|relevant_setting|relevant_endpoint" affected/path
```

then open only the useful surrounding ranges.

Do not use commands such as `rg -n "^"`, `cat` over many files, or equivalent patterns merely to dump complete files into context.

For large source/test files, avoid reading the whole file when the task concerns only a few symbols or sections. Read the relevant range first and expand only when dependencies require it.

Use one file-listing/search pass to discover scope where practical instead of repeatedly enumerating the repository.

## 3. Determine the complete scope

Before editing, identify:

- required behavior;
- affected components;
- likely files;
- existing tests;
- analogous implementations;
- documentation that may need a final update.

Do not expand the task without a technical reason.

Avoid unrelated refactoring.

## 4. Implement the complete task

Implement every requirement in the current request before considering the implementation complete.

Follow existing:

- architecture;
- naming;
- abstractions;
- dependency direction;
- code style;
- repository structure.

Prefer extending established patterns instead of introducing parallel ones.

## 5. Do not reread edited files without a reason

After a successful edit, assume the edit was applied.

Do not automatically perform:

- a full reread of the edited file;
- repeated `cat`, `sed`, or search calls just to confirm the write;
- `git diff` after every small edit.

Prefer:

`read -> understand -> edit -> targeted validation`

Reread only when:

- the edit failed or conflicted;
- a validation failure requires inspection;
- the next edit depends on exact current contents;
- multiple edits interact;
- the final diff reveals something unexpected.

## 6. Add or update tests

When application behavior changes, add or update appropriate tests.

Choose the smallest meaningful level:

- unit for isolated business logic;
- integration for boundaries such as repositories, databases, APIs, filesystems, or framework integration;
- E2E only for important complete scenarios.

For bug fixes, prefer:

1. regression test;
2. reproduce the failure when practical;
3. implement the fix;
4. rerun the regression test.

Do not create tests only to increase test count or coverage.

## 7. Normalize code before validation

Before read-only lint/format/type/test validation, run the project's safe deterministic auto-fix step for the affected scope.

Preferred interface:

`make fix`

or a component equivalent such as backend/frontend `make fix`.

Typical safe fixes include:

- formatter write mode;
- safe lint auto-fixes;
- import normalization.

Do not run a formatter/linter check first merely to discover issues the configured auto-fix command is expected to fix automatically.

Type checkers such as mypy, pyright, tsc, or vue-tsc are still validation tools, not generic auto-fixers. Write type-correct code during implementation, then run the smallest relevant type check after deterministic auto-fixes.

Tests are also validation, not an auto-fix step.

Preferred flow:

`implement -> make fix -> targeted type/tests -> targeted corrections -> make check`

## 8. Validate narrowly during development

Run the smallest check capable of confirming the current change.

Examples:

- one test;
- one test class;
- one test file;
- one affected package;
- lint for changed files;
- type checking for the affected component;
- backend-only checks for backend changes;
- frontend-only checks for frontend changes.

Normal development loop:

`edit -> targeted check -> fix -> targeted check`

Do not start with the complete CI pipeline.

## Validation deduplication

Before running broad checks, know what the project's aggregate targets already include.

Do not run a complete suite immediately before an aggregate target that will run the same suite again.

Examples:

- if `make check` includes all unit tests, use only changed/new targeted unit tests during implementation, then let `make check` run the full unit suite once;
- if `make verify` includes the full integration and E2E suites, do not run those complete suites separately immediately beforehand;
- if `make verify` already invokes `make check`, do not run both unless a concrete failure-isolation reason requires it.

Preferred validation plan:

```text
changed/new targeted tests
-> make fix
-> make check once
-> make verify once only when justified
-> infrastructure-specific smoke once when required and not already included
```

A broader target may intentionally repeat a small targeted test; avoid repeating entire suites.

Do not trade correctness for fewer checks. Remove only redundant coverage, not independent validation.

## 9. Handle failures with targeted reruns

When a check fails:

1. identify the specific failure;
2. determine the likely cause;
3. make the smallest necessary correction;
4. rerun only the relevant check.

Forbidden debugging loop:

`make ci -> fix -> make ci -> fix -> make ci`

Also avoid using `make check` or `make verify` repeatedly when only one test or one component is failing.

Preferred flow:

`broad check -> specific failure -> targeted fix -> targeted check -> broad check once`

## 10. Do not repeat successful checks unnecessarily

Do not rerun a successful check unless later changes could affect its result.

Examples:

- backend tests passed and only frontend documentation changed: do not rerun backend tests;
- Docker build passed and only a Python unit test changed: do not rebuild Docker;
- frontend checks passed and only backend code changed afterward: do not rerun frontend checks.

Every repeated validation must have a concrete technical reason.

## 11. Run the standard local check

After implementation and targeted validation stabilize, run the repository's fast project check, normally:

`make check`

It should usually cover lightweight checks such as:

- lint;
- formatting validation;
- static type checking;
- unit tests.

If it fails, return to targeted debugging. Rerun `make check` only after the specific failures are resolved.

## 12. Run extended verification only when justified

Use `make verify` only when the task requires broader local verification.

It may include:

- integration tests;
- cross-component checks;
- Docker configuration validation;
- selected E2E tests;
- other project-level checks.

Do not run it merely because the target exists.

## 13. Do not normally run full CI locally

The full CI target, normally `make ci`, is primarily for GitHub Actions.

Run it locally only when:

- explicitly requested;
- CI cannot otherwise be reproduced;
- the task specifically requires it;
- there is a concrete technical reason.

Expected local flow:

`make fix -> targeted checks -> make check -> optional make verify`

Expected remote flow:

`push -> GitHub Actions -> make ci`

## Command output discipline

Every command executed by Codex should use the most compact output mode that still preserves actionable failures.

This rule applies to:

- tests;
- linters;
- formatters;
- type checkers;
- Git commands;
- Make targets;
- package-manager commands;
- Docker / Docker Compose;
- build tools;
- migration tools;
- CI/log inspection;
- other CLI utilities.

Prefer:

- quiet/concise/summary flags;
- short tracebacks;
- machine-readable or filtered output when it is smaller and still useful;
- scoped commands that inspect only affected files/services;
- summaries for successful commands.

Avoid by default:

- verbose/debug modes;
- full stack traces for successful checks;
- full Docker/container logs;
- complete dependency-install logs when a concise mode exists;
- repeated command banners and echoed shell commands;
- dumping large successful test suites into context.

Examples:

```text
pytest -q --tb=short
git status --short
docker compose config -q
```

Use tool-specific compact modes rather than arbitrary truncation that could hide the real error.

If a compact command fails and its output is insufficient to diagnose the problem, rerun only the failing command or affected scope with the minimum additional verbosity required.

Preferred pattern:

```text
compact command
  -> success: continue
  -> failure with enough detail: fix
  -> failure without enough detail: rerun only that command with more detail
```

Do not request verbose output proactively "just in case".

## 14. Review the final diff once

Do not inspect `git diff` after every edit.

Start final review with compact metadata:

```text
git status --short
git diff --cached --check
git diff --cached --stat
git diff --cached --name-status
```

If the patch is modest and can be read without truncation, review the complete diff once.

If the patch is large, do not dump the entire patch into context. Review targeted diffs by risk area, for example:

- application/architecture changes;
- infrastructure/configuration;
- tests;
- security-sensitive code.

Documentation-only files usually need only targeted review when their content is relevant.

If a full diff is truncated, do not immediately repeat another large full diff. Inspect only the missing/high-risk paths.

Check for:

- unintended changes;
- unrelated files;
- generated artifacts;
- secrets;
- debug code;
- incomplete implementation;
- missing tests;
- accidental formatting damage.

## 15. Update documentation after implementation is stable

Do not continuously rewrite documentation while implementation is changing.

Update affected documentation only after:

1. implementation is complete;
2. necessary tests exist;
3. targeted checks pass;
4. `make check` passes;
5. optional extended verification is complete.

Potential files:

- `AGENTS.md`;
- `ARCHITECTURE.md`;
- root or component README files;
- API documentation;
- code docstrings.

Use the documentation skill for detailed documentation rules.

## 16. Commit and push

Stage only files belonging to the task.

Create a clear commit.

Never include:

- secrets;
- local environment files;
- unrelated untracked files;
- accidental generated artifacts.

Push only the task branch.

Do not push normal task changes directly to `develop` or `main`.

## 17. Pull Request and CI

Prepare or create a Pull Request:

`task branch -> develop`

GitHub Actions should perform the full independent CI validation.

Do not treat the PR as merge-ready while required checks fail.

If CI fails:

1. inspect only the relevant failure;
2. reproduce it locally with the smallest practical command when possible;
3. make a targeted fix;
4. run targeted validation;
5. run the appropriate fast check if affected;
6. push;
7. let CI rerun.

Do not ingest or reproduce unrelated successful CI logs.

## 18. Stop before merge

Codex must not automatically merge the Pull Request.

Responsibility boundary:

Codex:

`analyze -> implement -> test -> validate -> document -> commit -> push -> prepare PR -> CI`

Developer:

`review -> merge`

Do not merge into `develop` or `main` unless the user explicitly requests that separate action.

## Completion criteria

A task is complete when:

- the complete requested scope is implemented;
- required tests are added or updated;
- relevant targeted checks pass;
- the standard fast project check passes;
- extended verification was used when justified;
- the final diff was reviewed;
- required documentation is current;
- task changes are committed;
- the task branch is pushed;
- a Pull Request into the development branch is prepared;
- CI is running or completed.

## Final report

Keep the final response concise.

Report:

- what changed;
- tests added or updated;
- targeted checks performed;
- result of the standard local check;
- whether extended verification was needed;
- documentation changes;
- branch and commit status;
- PR / push status;
- CI status;
- remaining limitations.

Do not include long successful logs or a chronological list of tool calls.
