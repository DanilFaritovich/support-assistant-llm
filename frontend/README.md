# Support Assistant frontend

## Purpose

The frontend is a Vue 3 single-page application for reviewing the entire support-ticket workflow: enter or load a request, request automatic routing, confirm or override the proposed department, and generate a description from an editable template.

## Architecture and structure

```text
src/
├── App.vue                 # workflow state and user interface
├── api/tickets.ts          # typed HTTP client for ticket routes
├── api/workspace.ts        # settings reads/saves and bounded JSON import
├── components/WorkspaceManager.vue # workspace editor, transfer and restoration
├── demo.ts                 # prerender-only default examples and template
├── locale.ts               # URL locale and saved preference for root visits
├── messages.ts             # typed English/Russian interface and public copy
├── router.ts               # language routes; same workflow component across locales
├── app.ts                  # shared client/server application factory
├── entry-server.ts         # build-time Vue rendering without API calls
├── seo.ts                  # public origin, canonical/hreflang and metadata
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

Changing the ticket or applying saved workspace settings invalidates routing and drafting results. Editing the description template clears the previous generated description. Confirming the suggestion stores its ID locally. Choosing another department updates the same local final ID and does not call the routing endpoint again. The processing request always uses that final `department_id`.

## Backend interaction

The client uses relative routes so the same bundle works in development and behind Nginx:

- `GET /api/workspace` (initial authoritative settings and department load)
- `GET /api/workspace/defaults`
- `PUT /api/workspace`
- `GET /api/departments` (directory refresh)
- `POST /api/tickets/route`
- `POST /api/tickets/process`

Non-successful responses become typed HTTP errors and are presented in the selected interface language, without displaying backend detail strings. Vite proxies `/api` to `127.0.0.1:8000` in local development; the production Nginx image proxies it to the Compose `backend` service.

No OpenRouter key or LLM configuration is compiled into the frontend.
Production Nginx applies a general per-client anti-flood limit and a 16 KiB
request-body ceiling to `/api/`, independently from the backend's shared
Redis quota for LLM operations.

## Demo data

`src/demo.ts` supplies fictional examples and templates for build-time rendering
before any API request. After mounting, `/api/workspace` supplies authoritative
saved settings or backend-owned demo defaults. `WorkspaceManager.vue` edits a
separate draft; **Save workspace** persists it atomically with a revision.
Conflicts preserve edits and offer an explicit reload that discards them.
Department changes invalidate prior routing and confirmation.

Examples and templates may target English, Russian, or both. A named default
template overrides the language default. Editing text for the current ticket
does not update saved templates. Export downloads saved settings without a token
or revision. Import validates the file size/format locally and all business
constraints on the backend; import and demo restoration require confirmation
before replacing saved settings. Settings controls are disabled during LLM calls.

Saved data belongs to the browser cookie, expires after the backend-provided
retention period (90 days by default), and is never persisted in localStorage.
Only the interface language uses localStorage. No generated-ticket history is
stored; examples are persisted only through explicit settings saves.

## Interface language

The header provides English and Russian links to `/en/` and `/ru/`. The URL determines the language and takes priority over browser preferences. On a root visit, the client selects the saved `support-assistant.locale` preference, then Russian for a Russian browser language, or English otherwise. Without JavaScript, the root provides links to both languages. Switching works even when browser storage is unavailable. Vue Router preserves the workflow component across language changes and browser history navigation.

Switching language preserves entered text, the confirmed department, and generated results. Loading an example or template uses the current language. Department names/descriptions and LLM results retain the content supplied by the backend; the interface preference does not change the API or request a particular generation language.

## Static rendering and SEO

`npm run build` builds browser assets and a temporary server bundle, then `scripts/build.mjs` renders the initial Vue interface into `dist/en/index.html` and `dist/ru/index.html`. It also writes the language chooser, `sitemap.xml` and `robots.txt`. This rendering makes no backend or OpenRouter calls and contains no user input. The runtime remains static Nginx; no Node server is required. Vue hydrates the localized HTML and fetches workspace settings and departments after mounting.

Each language has its own title, description and canonical URL, plus reciprocal `hreflang` links for English, Russian and `x-default`. The confirmed public origin is `https://support.danil-miftakhov.dev`; this is a build contract, not evidence that DNS/TLS or deployment is configured. `VITE_SITE_ORIGIN` overrides it at build time and must be an HTTPS origin without a path, query or credentials. HTTP localhost origins are allowed for local preview:

```bash
VITE_SITE_ORIGIN=http://localhost:8080 npm run build
```

Compose forwards the same variable as a frontend build argument. The release workflow reads the public repository variable `VITE_SITE_ORIGIN`, falling back to the confirmed origin. Changing it requires rebuilding the image. It is not a backend runtime setting.

Production Nginx serves actual files, normalizes `/en` and `/ru` to trailing-slash URLs, and returns HTTP 404 for unknown paths. API proxying is unchanged. The build includes checks of the generated HTML and sitemap; component tests cover URL precedence, preserved form state, metadata updates and hydration.

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
