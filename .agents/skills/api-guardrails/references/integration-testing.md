# API Guardrails Integration and Testing Reference

Read this reference when wiring guardrails into FastAPI/gateway infrastructure, adding observability, or validating guardrail behavior.

## FastAPI integration

Keep generic transport guardrails at the presentation/infrastructure boundary.

FastAPI dependencies/middleware may enforce:

- request-size checks;
- authentication-derived identity;
- transport validation/correlation concerns.

Generic HTTP anti-flood should normally be enforced by the public gateway when present.

Expensive-operation/business quota belongs in application services through ports.

FastAPI should:

- determine trusted client identity;
- pass a plain `client_id` to the use case;
- map framework-independent quota exceptions to HTTP.

Pydantic schemas enforce field-level constraints. Domain/application code still enforces true business invariants.

## Reverse proxy integration

Configure Caddy/Nginx/proxy request-size and routing behavior consistently with application limits.

The gateway may reject obviously oversized requests before consuming backend resources.

Do not create contradictory proxy/application limits without documenting why.

## Logging

Log guardrail violations in controlled structured form when useful.

Safe context may include:

- route;
- limiter policy;
- request ID;
- allowed client/user identifier.

Do not log sensitive bodies.

For abusive high-volume traffic, prefer sampling/aggregation over flooding logs.

## Testing

Test guardrails that are part of the API contract.

Relevant cases include:

- input below limit succeeds;
- input above schema/body/upload limit fails as expected;
- edge anti-flood returns 429;
- quota allows requests below threshold;
- minute/day exhaustion is enforced;
- endpoints sharing one quota consume the same budget;
- different client IDs remain independent;
- `Retry-After` is propagated;
- concurrent consumes cannot overshoot an atomic limit;
- technical endpoints do not consume expensive quota;
- trusted identity selection works;
- gateway rate-limit configuration has a smoke/integration test when reasonable.

Do not make unit tests depend on real wall-clock delays when a testable clock/store abstraction can be used.

## Documentation

Document externally relevant limits when API consumers need them.

Do not expose internal anti-abuse thresholds when doing so creates unnecessary security risk.

At minimum, document operator/developer configuration.
