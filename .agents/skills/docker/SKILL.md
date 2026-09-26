---
name: docker
description: Docker and Docker Compose conventions for packaging full-stack applications, production-safe networking, health checks, minimal images, configuration, migrations, and one-command startup. Use when containerizing or changing application runtime infrastructure.
---

# Docker Standard

Package the application so that a developer or deployment environment can start the required services predictably with one documented command.

Prefer Docker Compose for multi-service local/deployment orchestration when it fits the project.

## Main goals

- reproducible builds;
- minimal production images;
- clear service boundaries;
- safe network exposure;
- explicit configuration;
- health checks;
- persistent state only where required;
- predictable startup and shutdown.

## One-command startup

Provide a documented entry point such as:

`docker compose up -d`

or a stable Make target such as:

`make up`

If development and production configurations differ, document both explicitly.

Do not require developers to manually start internal services one by one unless there is a strong reason.

## Dockerfiles

Prefer:

- explicit base image versions;
- multi-stage builds when they materially reduce the runtime image;
- dependency layers that make cache reuse effective;
- a non-root runtime user when practical;
- a minimal runtime image;
- deterministic dependency installation.

Do not bake secrets into images.

## .dockerignore

Use `.dockerignore` to exclude unnecessary build context.

Typical exclusions include:

- `.git`;
- virtual environments;
- `node_modules`;
- caches;
- coverage;
- local environment files;
- build outputs not required by the image;
- IDE files.

Do not exclude source or dependency metadata required for reproducible builds.

## Runtime configuration

Use environment variables or mounted configuration for runtime settings.

Never store production secrets in:

- Dockerfiles;
- Compose files committed with real values;
- image layers;
- source code.

Provide safe example configuration when useful.

## Production network model

For a browser-based full-stack application, expose only the public gateway/reverse proxy whenever practical.

Preferred production flow:

```text
Internet / Browser
       |
       v
Public gateway / reverse proxy
       |  HTTP anti-flood
       |
       +---- static frontend
       |
       +---- /api/* -> backend:8000
                         |
                         +----> database
                         |
                         +----> Redis (shared quota/cache state when enabled)
```

Backend and database should normally live on an internal Docker network and should not publish host ports in production.

The browser cannot call an internal Docker hostname directly. Public API traffic must reach the backend through the public gateway/reverse proxy.

Examples of public gateway technology include Caddy or Nginx.

## Nginx API anti-flood

When Nginx is used as the public gateway for a FastAPI application, place the general HTTP anti-flood limit at Nginx.

Apply the limit to the public API prefix, normally `/api/`.

Use a trusted client-IP key and configure:

- a normal request rate;
- a small burst;
- HTTP 429 for rejected requests.

Conceptual configuration:

```nginx
limit_req_zone $binary_remote_addr zone=api_per_ip:10m rate=<configured-rate>;

location /api/ {
    limit_req zone=api_per_ip burst=<configured-burst> nodelay;
    limit_req_status 429;
    proxy_pass http://backend;
}
```

The exact rate and burst are project configuration.

If Nginx is behind another trusted proxy/load balancer, configure Nginx real-IP handling correctly before using the client address as the limit key.

Do not expose backend ports publicly simply to implement rate limiting.

## Redis for distributed application quotas

When the application profile enables distributed quota state, include Redis in Docker Compose.

Redis should:

- be reachable by backend containers on the internal network;
- not publish a production host port unless operations explicitly require it;
- have a healthcheck;
- expose connection configuration through a backend environment variable such as `REDIS_URL`.

Example service intent:

```text
gateway/nginx
    |
    v
backend ----> redis
    |
    +-------> database
```

Backend startup should depend on Redis readiness when Redis is required for serving the configured use cases.

Use Compose health-based dependencies where supported and appropriate.

Do not store authoritative distributed quota state in backend container memory.

Redis persistence is not automatically required for short-lived rate-limit/quota state; choose persistence based on project requirements.

## Redis quota implementation

A Redis-backed rolling/sliding quota should execute the critical consume operation atomically.

For example, a Redis Lua script may:

1. remove entries outside each active window;
2. count current usage;
3. reject if any configured limit is reached;
4. calculate retry-after;
5. record the new request;
6. set/refresh key expiry.

Do not replace required rolling-window semantics with naive fixed-window `INCR + EXPIRE`.

Use keys that clearly separate:

- quota scope/resource;
- client identifier.

Endpoints intended to share the same quota must use the same quota scope.

## Development ports

Development may expose backend/database ports when required for debugging or local tooling.

Do not copy development exposure into production configuration automatically.

Keep production network rules stricter than local development rules.

## Compose networks

Use explicit networks where they improve isolation.

A common model:

- public/gateway network;
- internal application network.

Database services should normally only join the internal network.

Backend should join the network needed to communicate with the gateway and database.

## Volumes

Use persistent volumes only for state that must survive container replacement.

Examples:

- PostgreSQL data;
- intentionally persistent application storage.

Do not mount source-code volumes in production unless the deployment model specifically requires it.

## Health checks

Define meaningful health checks for long-running services.

A backend health endpoint should verify enough application readiness to be useful without performing expensive work.

Do not use a health check that always succeeds regardless of application state.

Compose/deployment ordering should rely on health/readiness where startup dependencies require it.

## Database migrations

Run schema migrations before the backend begins serving production traffic.

Preferred flow:

```text
build
 -> start required database
 -> run migration job/step
 -> start backend
 -> start/verify gateway
 -> health validation
```

Do not hide failing migrations inside an endless application restart loop.

## Frontend

For production Vue/static frontend builds:

- build assets in a dedicated build stage;
- serve compiled assets from the chosen gateway/static server;
- route API requests to the internal backend.

Do not ship the full Node development toolchain in the final static runtime image unless required.

## Backend

Backend containers should:

- install only required runtime dependencies;
- use the project's production server command;
- expose the container port internally;
- avoid publishing that port to the host in production when a gateway is present;
- handle termination gracefully.

## Database

PostgreSQL should:

- use persistent storage;
- use configuration from environment/secrets;
- remain internal in production;
- have a health check when other services depend on readiness.

## Validation

Provide lightweight validation commands when possible:

- `docker compose config` for configuration validation;
- targeted image build for changed services;
- health validation after startup.

Do not repeatedly rebuild every image after changes that cannot affect image contents.

Full build/start/health validation can run in GitHub Actions when it is expensive or verbose.

## Command and log output

Use compact Docker/Compose output during agent-driven checks.

Prefer validation/build modes that suppress routine progress while preserving failures.

For project Make targets, it is acceptable to capture verbose build/start output and:

- print a short success summary when the command succeeds;
- print the relevant captured tail/details only when it fails.

A successful Docker validation should ideally report only meaningful results such as:

```text
Compose config: OK
Redis: healthy
Backend: healthy
Gateway smoke: passed
```

Do not dump dependency download/build progress or full logs from every container after a successful startup.

When a service fails:

1. identify the failing service;
2. inspect only its relevant recent logs;
3. increase log scope/verbosity only if needed.

Avoid full `docker compose logs` output for the entire stack unless the failure genuinely spans multiple services.

Do not rebuild the complete stack when only one changed service/image requires validation and the project can safely validate that service independently.

## CI relationship

Local agent workflow should use targeted Docker checks.

GitHub CI may perform:

- complete image builds;
- Compose validation;
- migration startup checks;
- Redis health/readiness when Redis is enabled;
- service health checks;
- Nginx configuration validation;
- an API rate-limit smoke test when reasonable;
- selected E2E scenarios.

Do not use repeated full Docker logs as the normal local debugging loop.

## Security baseline

At minimum:

- no embedded secrets;
- minimal published ports;
- internal database/backend networking in production where possible;
- supported base images;
- non-root execution where practical;
- minimal packages in runtime images;
- explicit health/readiness behavior.

Adapt stricter security controls to the deployment environment.
