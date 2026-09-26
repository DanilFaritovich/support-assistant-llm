# Codex project guide

## Project

Support Assistant is a public demo that routes an IT support request to a
department and drafts a structured description with OpenRouter. The user always
reviews the proposed department. The OpenRouter key and all LLM calls stay in
the backend.

Stack: Python 3.14, FastAPI, Pydantic, async SQLAlchemy, Alembic, SQLite,
Redis, Vue 3, TypeScript, Vite, Vitest, Nginx, and Docker Compose.

The project follows the `fastapi-vue-clean` v5 profile from
[codex-development-standards](https://github.com/DanilFaritovich/codex-development-standards).
For standards updates, read `.codex-standards.lock.yaml` first and use the
project-local `standards-sync` skill. Read `catalog.yaml` first only during an
initial installation, and load only changed or newly applicable skills.

## Repository map

- `backend/app/api`: HTTP routes, request/response schemas, and dependencies.
- `backend/app/services`: application use cases and business rules.
- `backend/app/ports`: protocols owned by the application layer.
- `backend/app/connectors`: OpenRouter and Redis quota adapters.
- `backend/app/repositories`, `backend/app/db`: persistence adapters and
  SQLAlchemy infrastructure.
- `backend/app/core`, `backend/app/schemas`, `backend/app/prompts`:
  settings, centralized logging, validated models, and prompt loading.
- `backend/migrations`, `backend/resources`: schema migrations and
  repository-owned runtime resources.
- `backend/tests/{unit,integration,e2e}`: backend tests by scope.
- `frontend/src`: Vue application, API client, types, demo data, and tests.
- `.github/workflows`: CI entry points; project commands remain in Makefiles.
- `.agents/skills`: locked project-local development standards used by Codex.

Main entry points are `backend/app/main.py`, `backend/app/composition.py`,
`frontend/src/main.ts`, and `frontend/src/App.vue`.

Dependency direction is HTTP/UI and infrastructure -> application services ->
ports/domain contracts. Services must not depend on FastAPI, SQLAlchemy, or
OpenRouter implementations. See [ARCHITECTURE.md](ARCHITECTURE.md) for details.
Do not read that document for every small task; open it when changing module
boundaries, layers, database design, service interaction, infrastructure,
external integrations, or deployment architecture.

## Development rules

- Preserve the existing architecture, public API, naming, and dependency
  management unless the task requires a change.
- Keep developer-facing comments, docstrings, interfaces, and technical
  explanations in English. Comment constraints and reasons, not obvious code.
- Never commit credentials. `OPENROUTER_API_KEY` is backend-only; tracked
  environment examples contain placeholders only.
- Keep production LLM quota state in Redis through the application quota port.
  Process-local limiters are test/local doubles only.
- Keep generic public API anti-flood and request-body limits at Nginx. Derive
  application quota identity only through explicitly trusted proxy handling.
- Emit backend logs through the centralized configuration. Never log request
  bodies, credentials, API keys, authorization headers, or cookies.
- New business behavior requires meaningful tests. For a bug fix, prefer a
  regression test that fails before the fix, then run its narrow scope.
- Keep fixtures at the narrowest useful scope: test module first, local
  `conftest.py` when shared across modules, suite-level `conftest.py` only
  when broadly shared. Do not put fixtures in constants modules.
- Use `test_<component>_unit.py`, `test_<component>_integration.py`, and
  `test_<scenario>_e2e.py` for new backend tests. Add E2E tests only for
  important complete flows.

## Makefile and validation workflow

Makefiles are the stable project interface. Keep backend implementation in
`backend/Makefile`; keep frontend tool configuration in `package.json` and
make `frontend/Makefile` a thin wrapper. The root Makefile only orchestrates.

- `make fix`: safe backend/frontend lint and formatting auto-fixes.
- `make check`: fast read-only checks (lint, formatting, typing, unit tests).
- `make verify`: integration/E2E tests and the production frontend build;
  run after `make check` when the change warrants it.
- `make test`: all current backend and frontend tests.
- `make docker-build`, `make health`, `make docker-check`: explicit
  container validation; `docker-check` always performs cleanup.
- `make ci`: complete CI path; normally leave it to GitHub Actions.

Use scoped component targets during development. After a failure, diagnose it,
fix only the cause, rerun the smallest failing test/check until green, and then
run the relevant broader target once. Do not repeatedly run `make ci`. Do not
repeat a successful backend, frontend, or Docker check after unrelated changes.

Standard task workflow:

`AGENTS.md` -> define scope -> open only relevant files -> implement -> add
tests -> `make fix` -> targeted validation -> `make check` -> final diff -> update
documentation if needed -> push -> GitHub CI.

Run `make verify` between `make check` and the final diff for changes that
affect API/database integration, end-to-end behavior, builds, Docker, or CI.
Redis integration tests run when `TEST_REDIS_URL` is available; GitHub Actions
provides it through an isolated Redis service.

## Git and CI

- `main` is stable; `develop` is the integration branch.
- Start work from `develop` in `feature/...`, `fix/...`,
  `refactor/...`, `chore/...`, or `docs/...`.
- Merge task branches into `develop` through a Pull Request. Promote
  `develop` to `main` through a separate Pull Request.
- Do not perform ordinary development directly in `develop` or `main`, and
  do not merge a PR unless its required CI checks pass.
- Before commit/push, review the complete diff once for scope, generated files,
  and secrets. Do not add unrelated untracked files.

GitHub Actions runs `make ci` for PRs and pushes targeting `develop` or
`main`. Keep CI orchestration in Makefiles rather than duplicating tool
commands in workflow YAML.

## Documentation and context

Keep [README.md](README.md) and [README.ru.md](README.ru.md) synchronized.
Update them only after behavior and validation commands stabilize. Update
[ARCHITECTURE.md](ARCHITECTURE.md) only when the documented design changes.
Component details live in [backend/README.md](backend/README.md) and
[frontend/README.md](frontend/README.md).

Read the repository structure once per task, then open only files relevant to
the scope. Do not reread successfully edited files merely to confirm writes,
run `git diff` after every patch, or scan generated directories such as
`.venv`, `node_modules`, caches, coverage, and `dist`.
