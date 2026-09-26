---
name: api-guardrails
description: Core API protection rules for edge anti-flood, application quotas, trusted identity, bounded inputs/resources, and consistent errors. Load detailed references only for the affected guardrail.
---

# API Guardrails Standard

HTTP APIs should define explicit, centralized, configurable limits without scattering magic numbers through routers.

## Core model

Separate two different concerns:

1. **edge HTTP anti-flood** at the public reverse proxy;
2. **application/use-case quota** for expensive business operations.

```text
Client
-> public gateway / anti-flood
-> FastAPI presentation / trusted identity + transport validation
-> application use case
-> quota port
-> shared adapter/store when distributed consistency is required
```

Do not collapse these responsibilities into one process-local FastAPI limiter.

## Edge anti-flood

When a public reverse proxy exists, generic HTTP anti-flood belongs there.

Use trusted client identity, configured rate/burst behavior, and HTTP 429.

Do not trust spoofable forwarding headers.

For Nginx details, quota algorithms, Redis state, client identity, retry behavior, or limiter migration, read [references/rate-limiting-quota.md](./references/rate-limiting-quota.md).

## Expensive-operation quota

Business/resource quota belongs to the application use case.

The HTTP layer should only:

- determine trusted client identity;
- validate transport input;
- pass plain identity data such as `client_id: str`;
- map framework-independent application exceptions to HTTP.

Do not place business quota state in middleware, routers, domain entities, or production process-local counters.

Use an application port for the quota dependency.

Use shared state when limits must remain consistent across workers/containers/instances.

Technical health/readiness/version endpoints should not consume expensive-operation quota.

## Inputs and bounded resources

User-controlled inputs should have practical bounds.

Depending on endpoint type, define limits for:

- schema field lengths/ranges/collection sizes;
- request body size;
- uploads;
- text/document/template size;
- pagination;
- external-operation timeouts;
- concurrency/resource usage.

Reject oversized/invalid input before expensive downstream work.

For detailed resource-limit guidance, read [references/input-resource-limits.md](./references/input-resource-limits.md).

## Identity

Choose rate/quota identity deliberately.

Prefer authenticated user/account/client identity when available.

Anonymous traffic may use trusted client IP.

Do not pass transport/framework objects into application services only to discover identity.

## Configuration

Centralize guardrail settings.

Numeric limits are project/product policy and should be configurable where appropriate.

Endpoint-specific overrides should use a clear mechanism rather than duplicated numbers.

## HTTP behavior

Guardrail failures should use consistent API errors.

Rate/quota exhaustion should normally return HTTP 429 and useful retry information such as `Retry-After` when practical.

Oversized request bodies should use HTTP 413 where appropriate.

Do not expose internal limiter implementation details.

## Framework and gateway integration

Keep transport concerns at presentation/infrastructure boundaries and true business quotas in application services.

When implementing FastAPI/proxy integration, observability, or guardrail tests, read [references/integration-testing.md](./references/integration-testing.md).

## Testing requirement

Guardrails that are part of the API contract require tests at the smallest meaningful level.

Distributed quota behavior must validate shared-state/atomic semantics where those semantics matter.

## Documentation

Document consumer-visible limits when users need them and operator/developer configuration at minimum.

Do not expose sensitive anti-abuse thresholds without a reason.
