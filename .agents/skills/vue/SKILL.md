---
name: vue
description: Vue frontend conventions for API integration, component boundaries, state ownership, routing, composables, types, and keeping backend business data authoritative. Use when creating or modifying a Vue frontend that communicates with a backend API.
---

# Vue Frontend Standard

Build the frontend as a presentation client for backend capabilities.

The backend is the source of truth for persistent application/domain data and business decisions. The frontend owns presentation behavior and temporary UI state.

## Responsibility boundary

Frontend responsibilities include:

- rendering data;
- collecting user input;
- client-side validation for user experience;
- navigation and routing;
- loading and error states;
- temporary UI state;
- calling backend APIs;
- presentation formatting.

Do not implement backend business rules a second time in the frontend.

If a rule determines whether an operation is valid, allowed, persisted, routable, billable, or otherwise business-significant, the backend remains authoritative.

## Source of truth

Frontend may hold:

- fetched API data;
- temporary cache;
- form drafts;
- selected filters/tabs;
- optimistic UI state;
- loading state;
- local presentation preferences.

Do not use browser storage or frontend state as the authoritative persistence layer for core business data.

## Suggested structure

A simple default structure is:

```text
src/
├── api/
├── components/
├── composables/
├── router/
├── types/
└── views/
```

Adapt this to the existing project instead of forcing unnecessary restructuring.

## API layer

Centralize backend communication in `api/` or an equivalent module.

It should own:

- HTTP client configuration;
- endpoint clients;
- transport-level request/response handling;
- transport error normalization.

Do not scatter raw HTTP calls across unrelated components.

Prefer same-origin API paths such as:

`/api/...`

when a reverse proxy serves frontend and backend together.

Never use internal Docker hostnames such as `backend:8000` from browser code.

## Components

Components should focus on UI behavior.

Prefer:

- explicit props;
- explicit emits;
- small focused components;
- composition over oversized components.

Do not place complex API orchestration or business rules in presentational components.

## Views

Views/pages may coordinate page-level behavior:

- invoke API clients/composables;
- manage loading/error state;
- connect routing to UI;
- compose components.

Move reusable behavior into composables or dedicated modules.

## Composables

Use composables for reusable frontend behavior, for example:

- data fetching state;
- pagination;
- filters;
- form behavior;
- reusable UI interactions.

Do not use composables to duplicate backend business logic.

## Types

Use TypeScript types/interfaces when TypeScript is enabled.

Keep API transport types separate from UI-only state when that improves clarity.

Avoid implicit `any` for API data.

## Validation

Client-side validation improves user experience but does not replace backend validation.

The backend must validate all data required for correctness and security.

Simple validation rules may be mirrored in the UI for immediate feedback, but backend results remain authoritative.

## State management

Do not add a global store merely because one is available.

Use local/component state when sufficient.

Introduce Pinia or the project's chosen store when state is genuinely shared across unrelated areas or benefits from centralized lifecycle management.

Persistent business state still belongs to the backend.

## Routing

Use Vue Router when client-side routing is required.

Keep routes explicit and maintainable.

Frontend authorization guards improve UX only; backend authorization must enforce access independently.

## Configuration and secrets

Anything shipped to the browser must be considered public.

Never embed:

- server secrets;
- private API keys;
- database credentials;
- internal service credentials.

Use documented environment variables for public frontend configuration.

## Error handling

Handle expected API failures clearly.

Differentiate where useful between:

- validation errors;
- authentication/authorization errors;
- not-found/conflict errors;
- backend failures;
- network failures.

Do not display raw stack traces or internal backend exception payloads.

## Testing

Use:

- unit/component tests for isolated UI behavior;
- integration tests for interaction between components, composables, and API clients;
- E2E tests only for important user flows.

Follow the Vue testing standard for detailed conventions.

## Keep architecture proportional

Do not introduce complex feature/module architectures before the project needs them.

Prefer a simple, understandable frontend structure that can evolve when real complexity appears.
