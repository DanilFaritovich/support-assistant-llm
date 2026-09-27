# Production deployment contract

## Status and boundary

The repository contains the Continuous Delivery foundation for a future
single-VDS production deployment. It defines build, publish, migration, health,
and deployment orchestration, but no production server or credential has been
configured or verified yet.

Do not treat this foundation as an operational production deployment until the
external setup and the first controlled deployment have succeeded.

## Release and artifact flow

The production workflow runs only for the trusted `main` branch:

```text
develop -> reviewed Pull Request -> main
  -> build backend and frontend images in GitHub Actions
  -> publish commit-SHA tags to GHCR
  -> resolve immutable image digests
  -> protected production Environment
  -> synchronize version-controlled deployment artifacts
  -> explicit Alembic migration
  -> update services and wait for health
  -> verify the public URL
```

The VDS pulls the exact images produced by the workflow. It does not clone and
build application source. `latest` is not used as production state.

## GitHub `production` Environment

Create a protected Environment named `production`. Restrict it to `main` and
add reviewers if the deployment requires manual approval.

Environment variables:

| Name | Example shape | Purpose |
| --- | --- | --- |
| `DEPLOY_HOST` | `support.example.com` | SSH host or address |
| `DEPLOY_PORT` | `22` | SSH port |
| `DEPLOY_USER` | `support-deploy` | Dedicated non-root deployment user |
| `DEPLOY_PATH` | `/opt/support-assistant` | Stable server directory |
| `PRODUCTION_URL` | `https://support.example.com` | Public health-check origin |
| `PROXY_NETWORK` | `project-router` | Existing external Docker proxy network |
| `TRUSTED_PROXY_CIDR` | `172.20.0.0/16` | Exact Docker subnet trusted by Nginx |

Environment secrets:

| Name | Purpose |
| --- | --- |
| `DEPLOY_SSH_KEY` | Private key for the dedicated deployment user |
| `SSH_KNOWN_HOSTS` | Verified host-key entry for the target VDS |
| `PRODUCTION_ENV_FILE` | Complete multiline backend runtime environment |

`PRODUCTION_ENV_FILE` follows the tracked `.env.example` schema. At minimum,
set a real `OPENROUTER_API_KEY`, the public `OPENROUTER_SITE_URL`, and
`ENVIRONMENT=production`; retain the documented model, quota, timeout, and
logging settings as appropriate. Do not include image references, SSH data,
GitHub tokens, `DATABASE_URL`, `REDIS_URL`, or `FORWARDED_ALLOW_IPS`: Compose
owns those deployment values.

The workflow uses the built-in `GITHUB_TOKEN` only to publish packages. It does
not store that token on the VDS.

## One-time VDS setup

Prepare these prerequisites before enabling the workflow:

1. Provision a supported Linux VDS with Docker Engine and a recent Docker
   Compose v2 plugin that supports `up --wait` and `--wait-timeout`.
2. Create a dedicated non-root deployment user with key-based SSH access and
   permission to manage only the required Docker deployment.
3. Create `/opt/support-assistant` owned by that deployment user.
4. Create the external Docker network named by `PROXY_NETWORK` and record its
   exact subnet for `TRUSTED_PROXY_CIDR`.
5. Configure the public reverse proxy to route the application hostname to the
   `support-assistant-frontend` network alias on port 80 and to forward the
   client address and scheme.
6. Configure DNS, TLS, and the firewall. Only the public proxy and SSH ports
   should be reachable; backend and Redis remain internal.
7. Make the two GHCR packages public, or authenticate the deployment user to
   GHCR once with a read-only package credential if packages remain private.
8. Capture the VDS SSH host key through a trusted channel and store it in
   `SSH_KNOWN_HOSTS`; never disable host verification.
9. Populate and protect the GitHub `production` Environment inputs above.

Ensure the fixed `172.31.0.0/24` application subnet in
`compose.production.yml` does not conflict with existing VDS networks.

## Persistent server state

After deployment, the stable directory contains:

```text
/opt/support-assistant/
├── compose.production.yml       # synchronized from the deployed revision
├── Makefile                     # operational command interface
├── deploy/production.sh         # version-controlled deployment logic
├── .env                         # runtime secret, mode constrained by umask
├── .deployment.env              # proxy topology variables
├── .images.env                  # current immutable image references
└── .images.previous.env         # previous references when available
```

SQLite data remains in the `support-assistant-data` Docker volume. Redis quota
state is intentionally ephemeral.

## Deployment behavior

The deploy script validates both image references as GHCR digests, preserves
the previous image file, validates Compose, pulls required images, and starts
Redis. It then stops the backend before running the one-shot Alembic migration,
starts backend/frontend with bounded health waits, and verifies `/api/health`
through Nginx. GitHub Actions performs a second bounded check through
`PRODUCTION_URL` before reporting success.

A failed migration fails deployment and leaves the backend stopped. The script
does not perform an automatic database downgrade or claim that an image rollback
reverses persistent schema/data changes.

Operational commands in the stable directory:

```bash
make production-migrate
make production-health
make production-deploy \
  BACKEND_IMAGE=ghcr.io/owner/image@sha256:0000000000000000000000000000000000000000000000000000000000000000 \
  FRONTEND_IMAGE=ghcr.io/owner/image@sha256:0000000000000000000000000000000000000000000000000000000000000000
```

Normal production deployments must come from GitHub Actions, not manual image
selection. The Make targets exist for controlled recovery and diagnostics.

## Recovery boundary

If service replacement fails after a successful migration, inspect service
health and schema compatibility before restoring old application images. When
rollback is safe, restore `.images.previous.env`, validate Compose, start the
services with the three tracked env files, and rerun the gateway/public health
checks. Never automatically run an Alembic downgrade as part of image rollback.

The first real deployment belongs to the production-integration phase. Verify
SSH host checking, GHCR access, runtime file ownership, migration behavior,
container health, public routing, deployed digests, and the documented manual
recovery procedure during that controlled deployment.

## Repository-side validation

Without production access, validate the foundation with:

```bash
sh -n deploy/production.sh
make production-config
make check
make verify
make docker-check
```

These commands do not perform SSH deployment or require production secrets.
