---
name: backend-clean-architecture
description: Define a layered clean backend architecture with domain, application services, ports, adapters, repositories, connectors, and a presentation boundary. Use when creating or modifying backend structure, dependencies, business logic, persistence boundaries, or external integrations.
---

# Backend Clean Architecture

Use a layered architecture that keeps business logic independent from frameworks, databases, HTTP, and external services.

Adapt directory names to the existing repository when necessary. Preserve the dependency rules even when the physical layout differs.

## Core dependency rule

Dependencies point inward.

Conceptually:

```text
Presentation
     |
     v
Application
     |
     v
Domain

Adapters ----> Application Ports
Infrastructure supports Adapters and composition
```

Outer layers may depend on inner abstractions.

Inner layers must not depend on concrete outer frameworks.

## Domain

The domain contains the core business model and rules.

Typical contents:

- entities;
- value objects;
- domain exceptions;
- domain policies;
- pure business rules.

The domain must not depend on:

- FastAPI;
- SQLAlchemy;
- Alembic;
- HTTP clients;
- PostgreSQL;
- Docker;
- framework-specific request/response objects.

Prefer framework-free Python types and domain objects.

## Application

The application layer implements use cases and orchestration.

Typical contents:

- application services;
- use cases;
- commands / queries when useful;
- application-level DTOs when useful;
- ports.

Application services:

- coordinate domain behavior;
- call repositories and connectors through ports;
- define transaction/use-case boundaries;
- do not contain HTTP-specific behavior;
- do not depend on concrete database or API client implementations.

Business behavior belongs in domain/application, not in routers, repositories, connectors, or ORM models.

## Ports

Ports define interfaces required by the application.

Typical categories:

```text
application/
└── ports/
    ├── repositories/
    └── connectors/
```

Use Python `Protocol` or another project-standard interface mechanism.

Example:

```python
from typing import Protocol

class DepartmentRepository(Protocol):
    async def get_all(self) -> list[Department]:
        ...
```

Ports describe required behavior, not implementation details.

Do not expose SQLAlchemy sessions, HTTP response objects, or framework-specific types through application ports unless the project has an explicit reason.

## Resource/quota ports

Application-level resource policies that depend on shared infrastructure should be expressed as ports when they are required by a use case.

Examples:

- request/operation quota;
- distributed lock;
- idempotency store;
- usage counter.

For an LLM quota:

```python
from typing import Protocol

class LLMQuotaPort(Protocol):
    async def consume(self, client_id: str) -> None:
        ...
```

The application service calls the port before the expensive operation.

A concrete Redis implementation belongs in adapters/infrastructure.

Do not place this quota in the domain layer when it represents infrastructure/resource usage rather than a domain invariant.

Do not let the application layer depend on Redis types.

## Application exceptions and transport mapping

Application/use-case failures should use framework-independent exceptions.

For example:

```python
class LLMQuotaExceeded(Exception):
    retry_after: int
```

The application exception may carry transport-neutral data such as `retry_after`, but it must not depend on:

- FastAPI;
- `Request`;
- `HTTPException`;
- HTTP status codes;
- response headers.

The presentation layer decides that `LLMQuotaExceeded` maps to HTTP 429 and a `Retry-After` header.

This keeps the same use case callable from HTTP, CLI, jobs, or another transport without importing FastAPI.

## Repositories

Repositories are adapters for persistence.

They may use:

- SQLAlchemy;
- PostgreSQL;
- SQLite where appropriate;
- another configured persistence technology.

Repository responsibilities:

- query and persist data;
- map persistence models to domain/application objects when required;
- implement repository ports;
- hide persistence details from application services.

Repositories must not contain unrelated business rules.

Avoid hidden transaction commits inside repository methods unless the project's transaction model explicitly requires it.

Prefer transaction ownership at a clear use-case or unit-of-work boundary.

## Connectors

Connectors are adapters for external services and APIs.

Examples:

- LLM API;
- payment API;
- geocoder;
- third-party HTTP service;
- message broker client;
- remote storage.

Connector responsibilities:

- implement connector ports;
- perform protocol/API communication;
- translate external failures into adapter/application-level errors;
- map external payloads into internal representations.

Connectors must not own business decisions.

## Infrastructure

Infrastructure contains technical setup and concrete implementations that support adapters.

Examples:

- database engine/session setup;
- settings/configuration;
- logging configuration;
- HTTP client construction;
- migrations integration;
- application composition.

Infrastructure must not become a catch-all location for business logic.

## Presentation

Presentation is the external interface boundary.

Examples:

- FastAPI;
- CLI;
- Telegram bot;
- another transport.

Presentation may know which application use case or service it invokes, but it must not know how that business logic is implemented.

Presentation responsibilities:

- validate transport input;
- map input to application commands/arguments;
- obtain dependencies;
- invoke application services;
- map results/errors to transport responses.

## Suggested structure

A common layout is:

```text
app/
├── domain/
│   ├── entities/
│   ├── value_objects/
│   └── exceptions/
├── application/
│   ├── services/
│   └── ports/
│       ├── repositories/
│       └── connectors/
├── adapters/
│   ├── repositories/
│   └── connectors/
├── infrastructure/
│   ├── db/
│   ├── config/
│   └── logging/
└── presentation/
    └── ...
```

Do not force this exact directory tree onto an established repository if its current structure expresses the same boundaries clearly.

## Composition root

Concrete implementations should be wired at the outer boundary.

For example:

```text
FastAPI dependency / composition root
          |
          +--> TicketService
                  |
                  +--> DepartmentRepository port
                  |       ^
                  |       |
                  |   SQLAlchemyDepartmentRepository
                  |
                  +--> TicketRouting port
                  |       ^
                  |       |
                  |   LLMConnector
                  |
                  +--> LLMQuotaPort
                          ^
                          |
                    RedisLLMQuotaAdapter
```

Application services should receive dependencies rather than construct concrete adapters themselves.

## Models and schemas

Keep concepts distinct:

- domain models represent business concepts;
- application DTOs represent use-case inputs/outputs when needed;
- presentation schemas validate transport data;
- ORM models represent persistence.

Do not use one framework model as every layer's universal model merely for convenience.

Mapping is acceptable when it preserves boundaries and clarity.

## Change rules

When adding functionality:

1. identify the business use case;
2. place business behavior in domain/application;
3. define a port if the use case requires an external capability;
4. implement the port with an adapter;
5. expose the use case through presentation;
6. test each boundary at the appropriate level.

When reviewing code, treat business logic in HTTP handlers, SQLAlchemy models, repository query code, or API connectors as a likely boundary violation.
