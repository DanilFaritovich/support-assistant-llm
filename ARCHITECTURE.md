# Architecture

This document describes the current Support Assistant implementation. It is a
reference for changes to boundaries, persistence, integrations,
infrastructure, or deployment; it is not required reading for every small task.

## System overview

```text
Browser
  -> Nginx / compiled Vue SPA
       -> FastAPI HTTP API
            -> application services
                 -> department repository port -> SQLAlchemy adapter -> SQLite
                 -> routing/drafting ports -> OpenRouter adapters -> LLM
```

The browser calls relative `/api` URLs. In Docker Compose, Nginx serves the SPA
and proxies those requests to the backend on a private network. The backend owns
all model configuration, credentials, validation, and persistence.

## Backend components and layers

The backend uses a ports-and-adapters structure:

1. `app/api` translates HTTP requests and errors to application calls and
   response schemas.
2. `app/services` implements ticket routing, drafting, processing, and
   department-list use cases.
3. `app/ports` defines repository and LLM protocols required by services.
4. `app/connectors` and `app/repositories` implement those protocols for
   OpenRouter and SQLAlchemy.
5. `app/db`, `app/core`, `app/prompts`, and `app/schemas` provide
   infrastructure, validated settings, prompt resources, and data contracts.

`app/composition.py` constructs concrete dependencies. `app/main.py` owns
the FastAPI application lifecycle, database initialization/seed wiring, API
router registration, and safe exception mapping.

Dependencies point inward: adapters and HTTP composition may import
application contracts, while services do not import FastAPI, SQLAlchemy, or
OpenRouter implementations.

## Main data flows

### Startup and department directory

The container applies Alembic migrations before starting Uvicorn. Application
startup creates the async database resources and idempotently adds missing demo
departments from `backend/resources/departments.json`. Existing rows are not
overwritten. `GET /api/departments` reads the ordered directory through the
repository port.

### Ticket routing

1. `POST /api/tickets/route` validates the request.
2. The routing service loads the current department directory.
3. The OpenRouter routing adapter receives the ticket and allowed departments.
4. The adapter requests strict structured output and validates the response.
5. The service rejects a returned department ID outside the supplied directory.
6. The API returns the title, proposed department, and rationale.

### User confirmation and drafting

The browser stores the proposed department locally and requires confirmation.
A manual override changes that local ID without another LLM call.
`POST /api/tickets/process` resolves the submitted final `department_id`,
then the drafting service sends the actual department record, ticket text, and
template through the drafting port. Ticket results are returned to the browser;
they are not persisted.

## API and invariants

- `GET /api/health` and `GET /api/departments` do not invoke an LLM.
- `POST /api/tickets/route` and `POST /api/tickets/process` are the two LLM
  operations and share one per-client-IP rate limiter.
- The limiter permits 10 requests per rolling 60 seconds and 20 per rolling
  24 hours by default. It returns HTTP 429 with `Retry-After` when exceeded.
- Limiter state exists only in one backend process, resets on restart, and is
  not shared across workers or instances.
- Uvicorn may accept forwarded client addresses only from exact trusted proxy
  IPs/CIDRs configured with `FORWARDED_ALLOW_IPS`; wildcard trust is unsafe.
- `ticket_text` is limited to 4,000 characters and a custom `template` to
  2,000 characters at the backend boundary. Frontend limits are UX duplicates.
- A generated description always uses the user-submitted final department ID.
- OpenRouter models must be `openrouter/free` or explicit IDs ending in
  `:free`.

FastAPI exposes its generated OpenAPI schema and Swagger UI when the backend is
directly reachable in development.

## External LLM integration

OpenRouter is called through the async OpenAI-compatible SDK. The adapters use
repository-owned prompts, Pydantic-derived strict JSON Schema, compatible
provider filtering, a bounded timeout, and a small retry count. Parsed model
responses are validated before entering the application layer. Provider
failures and invalid output become safe API errors without provider details or
credentials.

`OPENROUTER_API_KEY` is read only by backend settings. It is never passed into
the Vue build, persisted in the database, or intentionally logged.

## Database

SQLite stores only the department directory. Async SQLAlchemy provides sessions
and the repository adapter; Alembic owns schema evolution. The local default is
`backend/data/app.db`; Compose stores the database at `/app/data/app.db` in
the `support-assistant-data` named volume.

Repository interfaces belong to the application boundary. Services operate on
validated records rather than SQLAlchemy models.

## Frontend

`frontend/src/main.ts` bootstraps the Vue application. `App.vue` owns the
short, linear workflow in local component state, so there is no global store.
`src/api/tickets.ts` is the typed HTTP adapter, `src/types/ticket.ts` holds
API types, and `src/demo.ts` holds fictional sample requests and the default
template.

Changing the ticket invalidates prior routing/drafting output. The frontend
does not contain department master data or OpenRouter configuration.

## Infrastructure and deployment

Docker Compose defines a backend service, a multi-stage frontend/Nginx service,
the private `support-assistant-network`, and the persistent SQLite volume.
Only Nginx is published to the host, at `127.0.0.1:8080`; the backend remains
on the Compose network. Both services provide healthchecks.

The named network may later be attached to ProjectRouter/Caddy. That deployment
must pass client addresses only through a trusted proxy chain and configure
`FORWARDED_ALLOW_IPS` narrowly.

## Verification boundaries

Backend tests are separated into unit, integration, and in-process API E2E
suites. Integration tests cover database/repository and external-adapter
boundaries with temporary databases and local HTTP transports. Frontend tests
cover component workflow and the API client with mocked `fetch`. Automated
tests do not call OpenRouter.

Makefiles are the stable execution interface: component Makefiles own their
tool commands, the root Makefile orchestrates project checks, and GitHub
Actions invokes the complete `make ci` path.
