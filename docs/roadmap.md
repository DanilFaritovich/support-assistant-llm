# Guest workspace roadmap and session handoff

Status: implemented, locally validated, committed, and pushed on
`feature/guest-workspaces`. [PR #10](https://github.com/DanilFaritovich/support-assistant-llm/pull/10)
targets `develop`; GitHub CI is running. Review and merge remain with the developer.
This file is the continuation point if the current session ends.

## Agreed scope and implemented behavior

- Keep SQLite, aiosqlite, async SQLAlchemy, and Alembic. No PostgreSQL migration.
- Offer a guest workspace without registration, email, or passwords.
- Isolate departments, example tickets, and named description templates by browser.
- Provide demo defaults, editable lists, a default template, JSON export/import,
  and confirmed restoration of demo settings.
- Preserve department confirmation and backend-only OpenRouter calls.
- Keep Redis LLM quotas keyed by trusted client IP, independent of guest tokens.
- Do not persist generated tickets or add accounts/shared workspaces.

The implementation checklist is complete:

- [x] Create a dedicated task branch from `develop`.
- [x] Add backend schema, repository port/adapter, service, routes, and wiring.
- [x] Add Alembic migration `9d5f41a8c201`; preserve existing department data.
- [x] Scope department reads and both LLM flows to the current guest space.
- [x] Add frontend editor, named/default templates, localized examples,
  import/export, restore confirmation, and recoverable errors.
- [x] Test isolation, persistence, revision conflicts including concurrent edits,
  foreign department selection, token handling, expiration/capacity, CSRF,
  settings limits, import/restore, and migration upgrade/downgrade.
- [x] Test frontend save/reload, custom examples/default templates, import/export,
  restore confirmation, conflicts, failed loads, and workflow invalidation.
- [x] Run normalization, scoped checks, `make check`, and `make verify`.
- [x] Build and start a separate temporary Docker stack; verify health and Nginx
  anti-flood with `make docker-check`; remove its containers and database volume.
- [x] Update both root READMEs, component docs, ARCHITECTURE.md, and AGENTS.md.
- [x] Review changes for scope, safe persistence, generated artifacts, and secrets.

## Key implementation decisions

- `guest_workspaces` stores each bounded settings aggregate as JSON. Whole-document
  saves, imports, and restorations are atomic. IDs are scoped to the document.
- The server creates a random 256-bit token. Only its SHA-256 hash is persisted;
  the token is held in an HttpOnly, SameSite=Lax cookie scoped to `/api`. Secure
  is enabled by default; local HTTP Compose explicitly disables it.
- Public demo reads create no rows. The first explicit save creates a space.
- Revisions protect against lost updates. Stale edits return 409 and remain in
  the frontend draft until the user explicitly reloads/discards them.
- Limits: 15,000 UTF-8 bytes, 20 departments, 20 examples, 10 templates; at least
  one department and one template. Keep Nginx's existing 16 KiB body limit.
- Expiration is 90 days after the last save by default, configurable with
  `GUEST_WORKSPACE_TTL_DAYS`. Expired rows are rejected on reads and deleted on
  writes. The default global capacity of 5,000 spaces is enforced atomically.
- Settings writes require a custom header and reject cross-site Fetch Metadata.
  CORS remains disabled. API responses are private/no-store. SQLAlchemy hides
  bound parameters in runtime database exception messages.
- Backend defaults are in `backend/resources/workspace.json`; frontend `demo.ts`
  supplies prerender placeholders only. Runtime settings come from the backend.

## Validation evidence

- `make fix`: passed.
- `make check`: passed (73 backend unit tests and 34 frontend tests).
- `make verify`: passed (integration/E2E suites, frontend production build and
  prerender checks, workflow/shell/Compose validation, deployment script tests).
- Three Redis integration tests skipped because `TEST_REDIS_URL` was unset.
  GitHub CI supplies an isolated Redis service and must run them.
- Subsequent scoped backend and frontend checks passed after final refinements.
  The final guest integration module has 10 passing scenarios; migration
  upgrade/downgrade and all 8 existing API E2E scenarios also passed.
- SQLite/aiosqlite integration tests hang inside this environment's sandbox and
  pass outside it. Use the approved elevated test execution path here.
- `make docker-check` passed with an isolated temporary Compose project,
  `support-assistant-guest-smoke`, on port 18080, without OpenRouter credentials.
  Its containers, network, and volume have been removed.
- The user's existing Compose stack on port 8080 was left running unchanged.
  It still serves the previous image until explicitly rebuilt/restarted.
- No real OpenRouter calls or production deployment were performed.

## Git delivery and next action

- Branch: `feature/guest-workspaces`, based on `develop`.
- Feature commit: `cf8831b` (`feat: add private guest workspaces and settings transfer`).
- Branch is pushed to `origin/feature/guest-workspaces`.
- [PR #10](https://github.com/DanilFaritovich/support-assistant-llm/pull/10) is open
  against `develop`; CI was in progress at handoff.
- Next action: inspect current PR checks. Fix a failure if one appears; otherwise
  the implementation is ready for developer review. Do not redo successful local
  checks unless code changes or a failure gives a reason.
- Do not merge without a separate user request.
- Do not stage the unrelated pre-existing untracked root `package.json` and
  `package-lock.json`.
- Git metadata is read-only inside the normal sandbox; approved elevated Git
  commands are required for branch creation, staging, and commits.
- If push authentication fails, retain the local commit, report the failure,
  and do not retry login or switch remote transport automatically.

## Later, only when needed

1. Revisit PostgreSQL when measured write contention or multiple backend hosts
   justify its operational cost. Migrate backups and integration tests together.
2. Attach a guest space to an account if recovery or cross-device sync is
   requested. Export/import covers the current demo's transfer use case.
3. Decide shared-workspace permissions and generated-ticket history separately;
   neither is part of the current feature.
