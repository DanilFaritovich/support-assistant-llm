# Input and Resource Limits Reference

Read this reference when changing request schemas, body/upload limits, pagination, timeouts, concurrency, or other bounded resource policies.

## Schema constraints

Validate practical semantic limits in request schemas.

For Pydantic models, use explicit constraints where appropriate:

- string min/max length;
- numeric ranges;
- collection/item limits;
- enum/literal values;
- nested constraints.

Do not accept unbounded user-controlled strings or collections when the domain has a practical maximum.

Limits should reflect product/domain needs rather than arbitrary implementation convenience.

## Request body size

Define a maximum HTTP request body size for user-controlled bodies.

Enforce it at the appropriate boundary:

- reverse proxy/gateway;
- ASGI/application middleware when required;
- upload handler for file endpoints.

Internet-facing production systems may use defense in depth.

Use HTTP 413 where appropriate for oversized requests.

Keep gateway and application limits consistent unless a deliberate difference is documented.

## File uploads

Define:

- maximum file size;
- allowed content types where meaningful;
- maximum file count;
- filename/path safety;
- streaming behavior for large accepted files.

Do not read an unbounded upload fully into memory.

Content-Type alone is not a security guarantee.

## Text/collection limits

For text-processing or LLM endpoints, define practical limits such as:

- maximum document/ticket length;
- maximum number of items;
- maximum template size;
- maximum metadata size.

When downstream token/model limits matter, account for them as well.

Reject oversized input before expensive downstream work.

## Pagination

List endpoints should have bounded pagination with:

- default page size;
- maximum page size;
- clear cursor/page rules.

Do not allow unbounded normal list requests.

## Timeouts

External operations should have explicit timeouts, including:

- HTTP services;
- databases;
- LLM APIs;
- other network dependencies.

Use configuration-driven values where appropriate.

## Concurrency and expensive work

Rate limiting does not replace resource/concurrency controls.

For expensive work consider:

- bounded concurrency;
- background jobs/queues;
- per-user quotas;
- upstream provider limits.

Do not hold request workers indefinitely for work that belongs in background processing.

## Configuration

Centralize guardrail settings instead of scattering numeric values through routers.

Typical settings may include:

```text
RATE_LIMIT_PER_MINUTE
RATE_LIMIT_PER_DAY
MAX_REQUEST_BODY_BYTES
MAX_UPLOAD_BYTES
DEFAULT_PAGE_SIZE
MAX_PAGE_SIZE
```

Endpoint-specific overrides should use a clear declarative mechanism.
