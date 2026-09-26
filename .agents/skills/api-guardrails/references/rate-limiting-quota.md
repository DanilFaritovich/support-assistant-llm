# Rate Limiting and Quota Reference

Read this reference when changing edge anti-flood, expensive-operation quotas, client identity, Redis quota storage, retry behavior, or rate-limit migration.

## Two-layer model

Keep separate:

1. edge HTTP anti-flood at the public reverse proxy;
2. application/use-case quota for expensive business operations.

Preferred architecture:

```text
Client
-> reverse proxy (generic /api/ anti-flood)
-> FastAPI presentation (trusted identity + transport validation)
-> application use case
-> quota port
-> shared quota adapter/store
```

Do not collapse these responsibilities into one process-local FastAPI limiter.

## Edge anti-flood

When Nginx is the public gateway:

- limit the public API prefix, normally `/api/`;
- key by trusted client IP;
- allow a small configured burst;
- return HTTP 429 on rejection;
- centralize rate/burst configuration;
- configure trusted real-IP handling if Nginx is behind another proxy.

Do not rate-limit on spoofable forwarding headers.

Conceptual configuration:

```nginx
limit_req_zone $binary_remote_addr zone=api_per_ip:10m rate=<configured-rate>;

location /api/ {
    limit_req zone=api_per_ip burst=<configured-burst> nodelay;
    limit_req_status 429;
    proxy_pass http://backend;
}
```

Exact numeric values are project policy.

## Application quota ownership

An LLM/business quota belongs to the application use case, not HTTP middleware.

The HTTP layer should:

- determine trusted client identity;
- validate transport input;
- pass plain `client_id: str`;
- map application exceptions to HTTP.

Do not keep business quota state in FastAPI middleware, router-local state, `app.state`, domain entities, or a production process-local limiter.

Technical endpoints such as health/readiness/version should not consume expensive-operation quota.

## Quota port and exception

Depend on a framework-independent application port, conceptually:

```python
class LLMQuotaPort(Protocol):
    async def consume(self, client_id: str) -> None:
        ...
```

Quota exhaustion should use a framework-independent application exception carrying retry information.

Application exceptions must not import FastAPI request/response concepts, status codes, or response headers.

FastAPI maps quota exhaustion to HTTP 429 and `Retry-After` using the project's normal error schema.

## Shared state

When quota must be consistent across workers/containers/instances, use shared state.

Redis is the default adapter for distributed short-window quota state when the project already uses or explicitly enables it.

In-memory quota is acceptable only for tests or explicitly single-process local development.

Do not present per-process limits as globally accurate in horizontally scaled deployments.

## Rolling/sliding windows

For rolling minute/day semantics, do not use naive fixed-window `INCR + EXPIRE` when boundary bursts would violate intended policy.

The critical operation must atomically:

- remove expired usage;
- count current usage;
- reject when a configured window is exhausted;
- record allowed usage;
- calculate retry time;
- maintain useful expiry.

A Redis Lua script or another Redis-side atomic mechanism is preferred.

Keys should separate quota scope/resource and client identity.

Endpoints intended to share one expensive resource budget must share the same quota scope/key.

## Multiple windows

Business quota may enforce several windows simultaneously, such as per minute and per day.

Keep values configurable, e.g.:

```text
LLM_RATE_LIMIT_PER_MINUTE
LLM_RATE_LIMIT_PER_DAY
REDIS_URL
```

Reject when any active window is exhausted.

`retry_after` should represent the relevant time until a request can succeed.

## Client identity

The transport layer determines client identity.

Prefer authenticated user/account/client ID when available. Anonymous traffic may use trusted client IP.

Do not pass FastAPI `Request` into application services merely to inspect IP addresses.

Do not trust arbitrary `X-Forwarded-For` from untrusted clients.

## Refactoring existing limiters

When replacing an existing limiter, preserve externally observable policy unless the task explicitly changes it:

- configured numeric limits;
- operations that consume quota;
- shared quota semantics;
- client identity semantics;
- error/retry behavior.

The refactor may change storage, algorithm, layer ownership, atomicity, or deployment topology.

After the new path is wired and tested, remove obsolete in-memory counters, app-state initialization, and duplicate HTTP-layer quota checks.

## HTTP behavior and endpoint policy

Rate-limit responses should:

- return HTTP 429;
- use a consistent error schema;
- provide `Retry-After` when practical;
- not expose internal implementation details.

Allow stricter policies for expensive/abuse-sensitive operations such as authentication, password reset, LLM inference, exports, file processing, external API fan-out, or expensive search.

Document intentional exemptions.

Rate-limit violations should be observable without generating excessive noisy logs.
