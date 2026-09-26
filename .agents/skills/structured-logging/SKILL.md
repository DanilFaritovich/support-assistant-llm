---
name: structured-logging
description: Structured application logging conventions using JSON logs, centralized configuration, correlation IDs, service context, safe event logging, and Loki/Grafana-compatible collection. Use when adding or reviewing backend logging and observability.
---

# Structured Logging Standard

Applications should emit structured logs that are easy to search, aggregate, and correlate in centralized logging systems.

For production services, prefer line-delimited JSON logs written to stdout/stderr. A log collector can then forward those logs to Loki, and Grafana can query and visualize them.

Do not design the application around Grafana reading application log files directly.

## Core principles

- use structured JSON in production;
- configure logging centrally;
- create module-level loggers instead of using `print()`;
- include enough context to trace a request or operation;
- log meaningful events, not every line of code;
- never log secrets or sensitive payloads by default;
- keep logging configuration environment-driven;
- make logs suitable for centralized collection.

## Logger usage

Python modules should normally define:

```python
import logging

logger = logging.getLogger(__name__)
```

Use the module logger inside services, repositories, connectors, infrastructure, and presentation code where meaningful events or failures need to be observable.

Do not create a different arbitrary logger name for every function.

Do not require a log statement in every function. Log at useful operational boundaries.

Typical useful locations:

- application service start/result for important operations;
- external connector calls and failures;
- repository failures or important persistence events;
- application startup/shutdown;
- background job lifecycle;
- authentication/security-relevant events;
- request completion at the HTTP boundary;
- unexpected exceptions.

## Central configuration

Logging must be configured in one explicit application-level location.

The configuration should control at least:

- log level;
- output format;
- service name;
- environment;
- JSON vs human-readable local format when supported;
- handler configuration.

Prefer environment variables such as:

- `LOG_LEVEL`;
- `LOG_FORMAT`;
- `SERVICE_NAME`;
- `ENVIRONMENT`.

Do not configure independent incompatible handlers throughout the codebase.

Libraries/modules should obtain loggers; the application entry point should configure them.

## JSON format

Production JSON logs should be one JSON object per line.

Useful fields include:

- `timestamp`;
- `level`;
- `logger`;
- `message`;
- `service`;
- `environment`;
- `request_id` when available;
- `trace_id` when tracing exists;
- `operation` or event name when useful;
- structured domain-safe context;
- exception information for failures.

Example:

```json
{
  "timestamp": "2026-09-26T12:00:00Z",
  "level": "INFO",
  "logger": "app.application.services.ticket",
  "message": "Ticket routed",
  "service": "support-assistant-backend",
  "environment": "production",
  "request_id": "8fb2...",
  "ticket_id": "42",
  "department_id": "7"
}
```

Do not build JSON log lines manually with string concatenation if the logging stack supports structured fields.

## Log levels

Use levels consistently.

### DEBUG

Use for detailed diagnostic information useful during troubleshooting.

Do not rely on DEBUG logs for required production auditing.

### INFO

Use for meaningful normal lifecycle/business-operation events.

Examples:

- application started;
- migration completed;
- important use case completed;
- external integration call completed when operationally useful.

### WARNING

Use for recoverable or suspicious conditions that deserve attention.

Examples:

- retry;
- degraded external dependency;
- invalid optional configuration fallback;
- rate-limit threshold approaching when explicitly implemented.

### ERROR / EXCEPTION

Use for failed operations.

When handling unexpected exceptions, include stack information through the logging framework.

Avoid logging the same exception at multiple layers unless each log adds distinct operational context.

## Correlation IDs

HTTP applications should attach a request/correlation ID to every request.

Preferred flow:

```text
incoming request
 -> accept trusted request ID or generate one
 -> attach to request context
 -> include in all logs for that request
 -> return it in the response when appropriate
```

Use context-local storage appropriate to the framework so concurrent requests do not share IDs.

For distributed systems, propagate correlation/trace IDs to supported downstream services.

## HTTP request logging

Request logging should normally include:

- method;
- normalized route/path;
- status code;
- duration;
- request ID;
- client identity metadata only when safe and useful.

Do not log full request/response bodies by default.

Avoid logging:

- passwords;
- access/refresh tokens;
- Authorization headers;
- cookies/session secrets;
- API keys;
- private keys;
- raw personal or confidential data unless explicitly required and governed.

## Business events

Log business events only when they are operationally meaningful.

Operationally queryable context must be emitted as structured fields when the logging stack supports them. Do not encode identifiers, statuses, durations, counts, or other fields needed for filtering/aggregation only inside the human-readable `message`.

Keep:

- `message` as a stable human-readable description;
- `event` as a stable machine-readable event name when useful;
- IDs, statuses, durations, counts, and other queryable context as separate structured fields.

Avoid:

```python
logger.info(
    "Ticket routed: department_id=%d",
    department.id,
)
```

Prefer:

```python
logger.info(
    "Ticket routed.",
    extra={
        "event": "ticket_routed",
        "ticket_id": ticket.id,
        "department_id": department.id,
    },
)
```

The exact structured-logging library/API may differ.

Do not duplicate the same queryable context only to make the message verbose. The message may summarize the event, while structured fields remain the source for machine filtering and aggregation.

Do not encode large objects or entire model dumps into routine logs.

## Repositories and connectors

Repositories:

- log unexpected persistence failures with useful safe context;
- avoid logging every successful trivial query;
- never log database credentials;
- avoid logging raw sensitive SQL parameters.

Connectors:

- log external service name/operation, latency/status when useful;
- log retry/failure context;
- redact credentials and sensitive payloads;
- do not dump complete external responses unless explicitly safe and needed.

## Container logging

In containers, default to structured JSON on stdout/stderr.

Preferred production path:

```text
application
 -> JSON stdout/stderr
 -> container/runtime log stream
 -> log collector
 -> Loki
 -> Grafana
```

A collector may be Grafana Alloy or another Loki-compatible collection mechanism selected by the deployment environment.

Do not require local persistent log files inside application containers unless there is a specific operational requirement.

## File logging

If file logs are explicitly required outside the normal container flow:

- use JSON Lines;
- use rotation;
- define retention;
- prevent unbounded disk growth;
- document file locations;
- keep collector configuration separate from application business code.

## Loki compatibility

Logs intended for Loki should remain structured and searchable.

Prefer low-cardinality metadata/labels at the collection layer.

Do not turn high-cardinality values such as request IDs, user IDs, or ticket IDs into Loki labels by default. Keep them in the JSON log body/fields so queries can parse them without exploding label cardinality.

## Grafana

Grafana is the visualization/query interface.

The expected flow is:

```text
structured logs -> Loki -> Grafana
```

Dashboards and queries should rely on stable fields such as service, environment, level, and parsed JSON content.

## Configuration example

A project should have one logging configuration module/file appropriate to its stack, for example:

```text
backend/
└── app/
    └── infrastructure/
        └── logging.py
```

or another existing configuration location.

It should configure formatters/handlers once and expose initialization from the application entry point.

## Testing

Test logging behavior when it represents an important contract, such as:

- request ID propagation;
- secret redaction;
- JSON formatter output;
- logging configuration initialization.

Do not write tests asserting every informational log message.

## Failure safety

Logging must not break the primary business operation because an optional contextual field is missing.

Logging configuration should fail early at application startup only when a required logging destination/configuration is truly mandatory.

## Performance

Avoid:

- expensive serialization for disabled log levels;
- dumping huge payloads;
- synchronous network logging directly from business code;
- logging inside tight loops without a concrete need.

Centralized shipping to Loki should normally happen outside business logic through the runtime/collector pipeline.
