---
name: api-guardrails
description: API protection conventions for rate limiting, request size limits, Pydantic input constraints, upload limits, trusted client identification, and consistent HTTP errors. Use when designing or modifying public/private HTTP APIs.
---

# API Guardrails Standard

Every HTTP API should define explicit resource and input limits.

Limits must protect the application without embedding arbitrary magic numbers throughout routers.

Use centralized, configurable defaults with per-endpoint overrides where the use case requires them.

## Two-layer rate limiting model

Do not treat all rate limiting as one concern.

For full-stack HTTP applications, separate:

1. **edge HTTP anti-flood protection** at the reverse proxy;
2. **application/use-case quota** for expensive business operations.

Preferred architecture:

```text
Client
  |
  v
Nginx / reverse proxy
  |  generic HTTP anti-flood for /api/
  v
FastAPI presentation layer
  |  identify client + validate transport
  v
Application service / use case
  |  quota_port.consume(client_id)
  v
Quota adapter
  |
  v
Shared store such as Redis
```

These layers solve different problems and must not be collapsed into one process-local FastAPI limiter.

### Edge HTTP anti-flood

When Nginx is the public gateway, apply a general per-client-IP request limit to the public API prefix, normally `/api/`.

Use Nginx request limiting such as `limit_req_zone` + `limit_req`.

Requirements:

- key by the trusted client IP;
- apply to `/api/`, not internal-only services;
- allow a small `burst` so short legitimate spikes are not rejected immediately;
- return HTTP 429 when the edge limit is exceeded;
- keep limits in clearly named configuration;
- avoid duplicating the same numeric values across multiple config fragments.

Conceptual example:

```nginx
limit_req_zone $binary_remote_addr zone=api_per_ip:10m rate=<configured-rate>;

location /api/ {
    limit_req zone=api_per_ip burst=<configured-burst> nodelay;
    limit_req_status 429;
    proxy_pass http://backend;
}
```

Exact values are project policy.

If environment-variable templating is already part of the deployment, limits may be templated from environment variables. Otherwise, prefer a clearly named Nginx config section over adding unnecessary templating complexity.

If Nginx itself is behind another proxy/load balancer, configure trusted real-IP handling. Do not rate-limit on spoofable forwarding headers.

### Application/use-case quotas

A quota for an expensive operation such as LLM inference is not an HTTP concern.

The HTTP layer should only:

- determine the client identifier, currently often the trusted client IP;
- validate the request;
- pass `client_id` into the application use case;
- map application exceptions to HTTP responses.

The application service/use case owns the decision to consume quota before the expensive operation.

Do not put an LLM/business quota in:

- FastAPI middleware;
- router-local state;
- `app.state` as process-local counters;
- domain entities;
- a process-local in-memory limiter in production.

The domain layer should remain unaware of transport quotas.

### Quota port

Represent the quota dependency through an application port.

Example:

```python
from typing import Protocol

class LLMQuotaPort(Protocol):
    async def consume(self, client_id: str) -> None:
        ...
```

The application service depends on this port and consumes quota before invoking the expensive connector.

If several endpoints perform the same expensive capability and are intended to share one quota, they must use the same quota scope/key.

For example, `/api/tickets/route` and `/api/tickets/process` should share one LLM quota when both consume the same LLM resource budget.

Technical endpoints such as health/readiness/version endpoints must not consume LLM quota.

### Application exception

Quota exhaustion should be represented by a framework-independent application exception.

Example:

```python
class LLMQuotaExceeded(Exception):
    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after
        super().__init__("LLM quota exceeded")
```

Application exceptions must not import or reference:

- FastAPI `Request`;
- `HTTPException`;
- HTTP status codes;
- response headers.

The presentation layer maps the exception to transport behavior.

### Shared quota store

When quota must be consistent across workers or backend instances, use a shared store.

Redis is the default adapter for distributed short-window quota state when the project already uses or explicitly enables it.

Do not use a production `InMemory*RateLimiter` for cross-request quota that must be consistent across:

- multiple Uvicorn/Gunicorn workers;
- multiple containers;
- multiple backend instances.

In-memory adapters are acceptable only for unit tests or explicitly single-process local development.

### Sliding/rolling windows

For minute/day quotas that are meant to represent rolling usage, use a rolling/sliding-window algorithm.

Do not implement rolling quota semantics with a naive fixed-window:

`INCR + EXPIRE`

when requests near a window boundary could exceed the intended rolling limit.

A Redis implementation may use sorted sets or another suitable structure.

The sequence:

- remove expired entries;
- count relevant entries;
- determine whether the new request is allowed;
- record the new request;
- calculate retry time;

must be atomic.

Prefer a Redis Lua script (or another Redis-side atomic mechanism) for this operation.

### Refactoring existing limiters

When replacing an existing rate limiter or quota implementation, preserve the current externally observable policy unless the task explicitly changes it.

For example, if the existing project defines:

```text
LLM_RATE_LIMIT_PER_MINUTE=10
LLM_RATE_LIMIT_PER_DAY=20
```

a refactor from an in-memory limiter to Redis must preserve those values and shared quota semantics.

The refactor may change:

- storage;
- algorithm implementation;
- layer ownership;
- atomicity;
- deployment topology.

It must not silently change:

- configured quota numbers;
- which operations consume the quota;
- whether endpoints share a quota;
- client identity semantics;
- error/retry behavior;

unless explicitly required.

When a process-local production limiter exists and distributed consistency is required, replace/remove it rather than layering the Redis quota on top of it.

Remove obsolete:

- in-memory counters;
- limiter initialization;
- `app.state` quota state;
- duplicated HTTP-layer quota checks;

after the new application-port/adapter path is wired and covered by tests.

## Multiple quota windows

A business quota may enforce several windows simultaneously, for example:

- per minute;
- per day.

Keep values configurable, for example:

```text
LLM_RATE_LIMIT_PER_MINUTE
LLM_RATE_LIMIT_PER_DAY
REDIS_URL
```

The application should reject a request when any configured quota window is exhausted.

`retry_after` should represent the relevant time until a request can succeed again.

### Client identity boundary

The transport layer determines the client identity.

For anonymous HTTP traffic this may be the trusted client IP.

For authenticated systems, a stable user/account/client identifier is usually preferable.

Pass the resulting plain `client_id: str` into the application layer.

Do not pass a FastAPI `Request` object into application services merely so they can inspect the IP address.

## Rate limiting

Public and user-facing API endpoints should be covered by a rate-limit policy unless there is a documented reason to exempt an endpoint.

Support multiple windows when appropriate, for example:

- requests per minute;
- requests per hour when useful;
- requests per day.

Do not hardcode one universal number into every route.

Prefer configuration such as:

- `RATE_LIMIT_PER_MINUTE`;
- `RATE_LIMIT_PER_DAY`;
- route-specific overrides.

The actual numeric values are project/product policy and should be selected during initialization or configuration.

## Rate-limit identity

Choose the limiter key deliberately.

Possible identities include:

- authenticated user/account ID;
- API key/client ID;
- IP address for anonymous traffic;
- a combination of identity and endpoint.

Prefer authenticated identity when available.

Do not trust arbitrary `X-Forwarded-For` values from untrusted clients.

When deployed behind a reverse proxy, configure trusted proxy handling so client IP extraction cannot be trivially spoofed.

## Distributed deployments

For more than one backend instance, use shared rate-limit state when limits must be globally consistent.

A shared store such as Redis is a common solution.

In-memory limiting is acceptable only when:

- the application is single-instance;
- the environment is local/test;
- approximate per-instance limiting is explicitly acceptable.

Do not present per-process memory limits as globally accurate in a horizontally scaled deployment.

## HTTP response

When a rate limit is exceeded:

- return HTTP 429;
- use a consistent error schema;
- provide retry information such as `Retry-After` when practical;
- do not expose internal limiter implementation details.

Rate-limit failures should be observable through metrics/logging without producing excessive noisy logs.

## Endpoint policies

Allow stricter limits for expensive or abuse-sensitive operations.

Examples:

- authentication;
- password reset;
- LLM inference;
- file processing;
- exports;
- external API fan-out;
- expensive search.

Cheap read endpoints may use a different policy.

Document intentional exemptions.

## Input constraints

Validate semantic input constraints using schemas.

For Pydantic models, define explicit constraints where appropriate:

- string `min_length` / `max_length`;
- numeric ranges;
- list/set item limits;
- collection lengths;
- enum/literal values;
- nested object constraints.

Do not accept unbounded user-controlled strings or collections when the domain has a practical maximum.

Input limits must reflect product/domain needs rather than arbitrary implementation convenience.

## Request body size

Define a maximum HTTP request body size for endpoints that accept user-controlled bodies.

Enforce it at the most appropriate boundary:

- reverse proxy/gateway;
- ASGI/application middleware when required;
- upload handler for file endpoints.

Prefer defense in depth for internet-facing production deployments.

When the request is too large, return HTTP 413 where appropriate.

## File uploads

For upload endpoints define:

- maximum file size;
- allowed content types when meaningful;
- file count;
- filename/path safety;
- streaming behavior for large accepted files.

Do not read an unbounded upload fully into memory.

Content-Type alone must not be treated as a security guarantee.

## Text and collection limits

For text-processing/LLM endpoints, define limits such as:

- maximum ticket/document length;
- maximum number of items;
- maximum template size;
- maximum metadata size.

If token-based model limits matter, validate both practical input size and downstream model constraints where appropriate.

Reject oversized input before expensive downstream processing.

## Pagination

List endpoints should have bounded pagination.

Define:

- default page size;
- maximum page size;
- cursor/page rules.

Do not allow a client to request an unbounded dataset in one normal API request.

## Timeouts

Expensive external operations should have explicit timeouts.

Do not allow user requests to wait forever on:

- external HTTP services;
- databases;
- LLM APIs;
- other network dependencies.

Timeout values are project-specific and should be configuration-driven where appropriate.

## Concurrency and expensive work

Rate limiting is not a replacement for concurrency/resource controls.

For expensive endpoints, consider:

- bounded concurrency;
- background jobs/queues;
- per-user quotas;
- upstream provider limits.

Do not hold HTTP workers indefinitely for workloads that belong in background processing.

## Configuration

Centralize API guardrail settings.

A project may expose settings such as:

```text
RATE_LIMIT_PER_MINUTE
RATE_LIMIT_PER_DAY
MAX_REQUEST_BODY_BYTES
MAX_UPLOAD_BYTES
DEFAULT_PAGE_SIZE
MAX_PAGE_SIZE
```

Endpoint-specific policies may override defaults through a clear declarative mechanism.

Do not scatter duplicated numeric limits across routers.

## FastAPI integration

Keep generic transport guardrails at the presentation/infrastructure boundary.

FastAPI dependencies or middleware may enforce:

- request size limits;
- authentication-derived identity;
- transport-level validation/correlation concerns.

Generic HTTP anti-flood should preferably be enforced by the public reverse proxy when that gateway exists.

Expensive-operation/business quotas belong in application services through ports, not in FastAPI middleware or process-local application state.

FastAPI should:

- determine the trusted client identifier;
- pass a plain `client_id` to the use case;
- map application quota exceptions to HTTP.

For an exception such as `LLMQuotaExceeded(retry_after=...)`, FastAPI should return:

- HTTP 429 Too Many Requests;
- `Retry-After: <seconds>`;
- the project's normal error schema.

Pydantic schemas enforce field-level constraints.

Business services should receive already validated bounded inputs, but domain invariants must still be enforced in domain/application code when they are true business rules.

## Reverse proxy integration

When using Caddy, Nginx, or another gateway, configure request-size/proxy behavior consistently with the application limits.

The gateway may reject obviously oversized requests before they consume backend resources.

Do not create contradictory gateway/application limits without documenting the reason.

## Logging

Log limit violations in a controlled structured form when operationally useful.

Include safe context such as:

- route;
- limiter policy;
- request ID;
- authenticated client/user identifier when allowed.

Do not log sensitive request bodies.

Avoid flooding logs for abusive traffic; sampling/aggregation may be more appropriate at high volume.

## Testing

Add tests for guardrails that are part of the API contract.

Examples:

- request below an input limit succeeds;
- request above a field length fails;
- oversized payload returns the expected error;
- Nginx/API anti-flood returns 429;
- a quota window allows requests below the threshold;
- minute quota exhaustion is enforced;
- daily quota exhaustion is enforced;
- several endpoints that share one business quota consume the same quota;
- different client IDs have independent quotas;
- `Retry-After` is propagated correctly;
- concurrent quota consumes cannot overshoot the configured limit;
- technical endpoints do not consume an expensive-operation quota;
- trusted identity selection works;
- Nginx rate-limit configuration has a smoke/integration test when reasonable for the existing test setup.

Do not make unit tests depend on real wall-clock delays when the limiter can use a testable clock/store abstraction.

## Documentation

Document externally relevant limits when API consumers need to know them.

Do not expose internal anti-abuse thresholds if doing so would create unnecessary security risk.

At minimum, keep operator/developer configuration documented.
