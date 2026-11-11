# Support Assistant frontend

## Purpose

The frontend is a Vue 3 single-page application for reviewing the entire support-ticket workflow: enter or load a request, request automatic routing, confirm or override the proposed department, and generate a description from an editable template.

## Architecture and structure

```text
src/
├── App.vue                 # workflow state and user interface
├── api/tickets.ts          # typed HTTP client for relative /api routes
├── demo.ts                 # fictional tickets and generic template
├── locale.ts               # typed English/Russian copy and language preference
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

Non-successful responses become typed HTTP errors and are presented in the selected interface language, without displaying backend detail strings. Vite proxies `/api` to `127.0.0.1:8000` in local development; the production Nginx image proxies it to the Compose `backend` service.

No OpenRouter key or LLM configuration is compiled into the frontend.
Production Nginx applies a general per-client anti-flood limit and a 16 KiB
request-body ceiling to `/api/`, independently from the backend's shared
Redis quota for LLM operations.

## Demo data

`src/demo.ts` contains three fictional requests and one generic description template in each supported language. Users can load an example, edit every field, clear it, or enter their own request. Department data comes from the backend database rather than being duplicated in the UI.

## Interface language

The header provides English and Russian buttons. A saved `support-assistant.locale` preference takes priority; otherwise a Russian browser language selects Russian and other browser languages select English. Switching works even when browser storage is unavailable. The document language and title follow the selection.

Switching language preserves entered text, the confirmed department, and generated results. Loading an example or template uses the current language. Department names/descriptions and LLM results retain the content supplied by the backend; the interface preference does not change the API or request a particular generation language.

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
make fix           # npm run lint:fix + npm run format
make lint          # npm run lint
make format-check  # npm run format:check
make typecheck     # npm run typecheck
make test-unit     # npm run test
make test          # npm run test
make check         # npm run check
make build         # npm run build
make all           # check + production build
```

The Makefile is a thin wrapper around the scripts in `package.json`; npm remains
the source of the frontend quality-tool configuration.

The component suite covers demo loading, routing review, confirmation, manual override, final API payloads, reset behavior, and error recovery. API-client tests mock `fetch`; no external service is contacted.
