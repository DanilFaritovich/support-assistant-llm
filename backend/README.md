# Support Assistant backend

## Purpose

The backend exposes the support-ticket API, owns the OpenRouter credential, validates model output, persists the IT-department directory, and generates descriptions using the user's final department selection.

## Architecture

The code follows ports-and-adapters boundaries:

```text
HTTP routes -> application services -> ports -> adapters
    |                  |                  |-> OpenRouter connectors
    |                  |                  `-> SQLAlchemy repository
    `-> Pydantic API schemas                    |
                                                `-> SQLite
```

FastAPI dependencies compose concrete adapters. Business services do not import FastAPI or OpenRouter-specific configuration.

## Module structure

```text
app/
├── api/             # routes, HTTP schemas, dependency composition contracts
├── connectors/      # OpenRouter through the OpenAI-compatible async SDK
├── core/            # validated environment settings
├── db/              # SQLAlchemy base, models, sessions, idempotent demo seed
├── ports/           # repository, routing, and drafting protocols
├── prompts/         # loading of repository-owned generic prompts
├── repositories/    # SQLAlchemy department adapter
├── schemas/         # domain and LLM result models
├── services/        # routing, drafting, department, and processing use cases
├── composition.py   # dependency construction
└── main.py          # application lifecycle and safe exception mapping
resources/
├── departments.json
└── prompts/
migrations/          # Alembic environment and initial schema
tests/               # unit, integration, and in-process API tests
```

## Business flow

1. `GET /api/departments` returns the available directory.
2. `POST /api/tickets/route` loads all departments and asks the routing port for a title, department ID, and rationale.
3. The route rejects IDs not present in the supplied directory.
4. The browser confirms or changes the ID locally.
5. `POST /api/tickets/process` looks up the submitted final ID and passes the actual department record to the drafting port.

Manual reassignment therefore needs no backend endpoint and never triggers a second routing completion.

## API

### `GET /api/health`

Returns `{"status":"ok"}` for container and proxy healthchecks.

### `GET /api/departments`

Returns an ordered list of `{id, name, description}` records.

### `POST /api/tickets/route`

Request:

```json
{"ticket_text": "The employee portal returns Session expired after sign-in."}
```

Response:

```json
{
  "title": "Portal session expires after sign-in",
  "department_id": 3,
  "department_name": "Identity & Access",
  "reasoning": "The reported failure occurs during sign-in."
}
```

### `POST /api/tickets/process`

Request:

```json
{
  "ticket_text": "The employee portal returns Session expired after sign-in.",
  "department_id": 3,
  "template": "Summary:\n\nActual result:\n\nExpected result:"
}
```

Response: `{"description":"..."}`.

FastAPI also generates OpenAPI at `/openapi.json` and Swagger UI at `/docs`.

## Database and migrations

The default non-container database is `backend/data/app.db`. Docker Compose overrides it with `/app/data/app.db` on a named volume. The container runs `alembic upgrade head` before Uvicorn.

The initial migration creates the unique department table from `resources/departments.json`. On every startup, `seed_demo_departments` adds only names that do not already exist. Existing records are never overwritten, and repeated startup creates no duplicates.

## OpenRouter integration

The backend uses `https://openrouter.ai/api/v1` through the async OpenAI-compatible SDK. The default `openrouter/free` router automatically selects an available free model. A comma-separated list of explicit `:free` model IDs can be supplied as a fallback order; any paid model ID fails configuration validation.

Each request includes:

- a strict JSON Schema response format generated from its Pydantic result model;
- `provider.require_parameters=true`, so only compatible providers are used;
- the configured free-model fallback list;
- a bounded timeout and 0–3 SDK retries.

The connector then validates JSON, required types, forbidden extra fields, non-empty text, and routing membership. Free-model exhaustion, API errors, or malformed responses are returned as a safe HTTP 502 message without leaking provider details.

## Configuration

Copy `.env.example` to `.env` for a direct backend run, or use the root `.env` with Compose.

| Variable | Default | Notes |
| --- | --- | --- |
| `OPENROUTER_API_KEY` | none | Required for routing and drafting; backend only |
| `OPENROUTER_MODELS` | `openrouter/free` | Only the free router and `:free` IDs are accepted |
| `OPENROUTER_TIMEOUT_SECONDS` | `60` | Must be between 1 and 180 |
| `OPENROUTER_MAX_RETRIES` | `2` | Must be between 0 and 3 |
| `OPENROUTER_SITE_URL` | none | Optional OpenRouter attribution header |
| `LLM_RATE_LIMIT_PER_MINUTE` | `10` | Shared per-IP LLM operation limit over 60 seconds |
| `LLM_RATE_LIMIT_PER_DAY` | `20` | Shared per-IP LLM operation limit over 24 hours |
| `DATABASE_URL` | local SQLite | Any async SQLAlchemy URL supported by installed drivers |

The two ticket endpoints share an in-memory rate limiter. Its state resets when
the process restarts and is not shared across workers or backend instances.
Behind a reverse proxy, set Uvicorn's `FORWARDED_ALLOW_IPS` environment variable
to exact trusted proxy IPs/CIDRs and never to `*`.

## Local run

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.dev.txt
cp .env.example .env
# Set OPENROUTER_API_KEY
.venv/bin/python -m alembic upgrade head
.venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Testing and quality

```bash
make lint PYTHON=.venv/bin/python
make format-check PYTHON=.venv/bin/python
make typecheck PYTHON=.venv/bin/python
make test-unit PYTHON=.venv/bin/python
make test-integration PYTHON=.venv/bin/python
make test-e2e PYTHON=.venv/bin/python
make test PYTHON=.venv/bin/python
make check PYTHON=.venv/bin/python
```

`make check` is the fast development target: lint, formatting, mypy, and unit
tests. The scoped integration and E2E targets are orchestrated by the root
`make verify`; `make test` runs all three backend test levels.

Unit tests cover service rules, strict LLM response validation, free-only configuration, fallback request parameters, retry/timeout configuration, and error handling. Integration tests use temporary SQLite databases and `httpx.MockTransport`. End-to-end API tests run the FastAPI lifespan in process. No automated test makes a real OpenRouter request.
