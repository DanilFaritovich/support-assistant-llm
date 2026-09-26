# Support Assistant frontend

## Purpose

The frontend is a Vue 3 single-page application for reviewing the entire support-ticket workflow: enter or load a request, request automatic routing, confirm or override the proposed department, and generate a description from an editable template.

## Architecture and structure

```text
src/
├── App.vue                 # workflow state and user interface
├── api/tickets.ts          # typed HTTP client for relative /api routes
├── demo.ts                 # fictional tickets and generic template
├── types/ticket.ts         # API request/response types
├── style.css               # responsive global component styles
├── main.ts                 # Vue bootstrap
└── __tests__/              # component and API-client tests
```

The application intentionally uses local component state rather than a global store: it manages one ticket at a time and has a short, linear workflow.

## Main interface states

- Department directory: loading, loaded, empty, and error states.
- Routing: idle, loading, result, and error states.
- Department review: unconfirmed proposal, manual selection, and confirmed result.
- Drafting: editable template, loading, generated result, and recoverable error.

Changing the ticket invalidates routing and drafting results. Confirming the suggestion stores its ID locally. Choosing another department updates the same local final ID and does not call the routing endpoint again. The processing request always uses that final `department_id`.

## Backend interaction

The client uses relative routes so the same bundle works in development and behind Nginx:

- `GET /api/departments`
- `POST /api/tickets/route`
- `POST /api/tickets/process`

Non-successful responses use FastAPI's `detail` string when available and otherwise show a status-based fallback. Vite proxies `/api` to `127.0.0.1:8000` in local development; the production Nginx image proxies it to the Compose `backend` service.

No OpenRouter key or LLM configuration is compiled into the frontend.

## Demo data

`src/demo.ts` contains three fictional requests and one generic description template. Users can load an example, edit every field, clear it, or enter their own request. Department data comes from the backend database rather than being duplicated in the UI.

## Local development

Start the backend first, then:

```bash
npm ci
npm run dev
```

Open <http://127.0.0.1:5173>.

## Quality commands

```bash
make install       # npm ci
make lint          # npm run lint
make format-check  # npm run format:check
make typecheck     # npm run typecheck
make test          # npm run test
make check         # npm run check
make build         # npm run build
make all           # check + production build
```

The Makefile is a thin wrapper around the scripts in `package.json`; npm remains
the source of the frontend quality-tool configuration.

The component suite covers demo loading, routing review, confirmation, manual override, final API payloads, reset behavior, and error recovery. API-client tests mock `fetch`; no external service is contacted.
