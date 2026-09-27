# Production deployment contract

## Status and boundary

The repository contains the Continuous Delivery foundation for a future
single-VDS production deployment. It defines build, publish, migration, health,
and deployment orchestration, but no production server or credential has been
configured or verified yet.

Do not treat this foundation as an operational production deployment until the
external setup and the first controlled deployment have succeeded.

## Release and artifact flow

The foundation workflow is manual and accepts only the trusted `main` branch:

```text
develop -> reviewed Pull Request -> main
  -> manual workflow dispatch
  -> reusable CI for the exact main commit
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
| `APPLICATION_SUBNET` | `172.31.0.0/24` | Dedicated private subnet selected to avoid existing VDS networks |
| `DEPLOY_HOST` | `support.example.com` | SSH host or address |
| `DEPLOY_PORT` | `22` | SSH port |
| `DEPLOY_USER` | `support-deploy` | Dedicated non-root deployment user |
| `DEPLOY_PATH` | `/opt/support-assistant` | Stable server directory |
| `FRONTEND_INTERNAL_IP` | `172.31.0.3` | Nginx address inside `APPLICATION_SUBNET`, trusted by Uvicorn |
| `PRODUCTION_URL` | `https://support.example.com` | Public health-check origin |
| `PROXY_NETWORK` | `project-router` | Existing external Docker proxy network |
| `TRUSTED_PROXY_IP` | `172.20.0.2` | Exact reverse-proxy container address trusted by Nginx |

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
2. Create a dedicated non-root deployment user with key-based SSH access.
   Access to the host Docker socket or membership in the Docker group normally
   grants host-equivalent control; the non-root login is not a strong isolation
   boundary. Use rootless Docker or a constrained deployment service if the
   threat model requires stronger separation.
3. Create `/opt/support-assistant` owned by that deployment user.
4. Inspect existing Docker and host routes. Select a non-conflicting dedicated
   `APPLICATION_SUBNET` and an unused `FRONTEND_INTERNAL_IP` inside it; do not
   copy the examples without checking the VDS.
5. Create the external Docker network named by `PROXY_NETWORK`. Give the public
   reverse proxy a stable address on that network and record that exact address
   as `TRUSTED_PROXY_IP`; do not trust the whole shared network subnet.
6. Configure the public reverse proxy to route the application hostname to the
   `support-assistant-frontend` network alias on port 80 and to forward the
   client address and scheme.
7. Configure DNS, TLS, and the firewall. Only the public proxy and SSH ports
   should be reachable; backend and Redis remain internal.
8. Make the two GHCR packages public, or authenticate the deployment user to
   GHCR once with a read-only package credential if packages remain private.
9. Capture the VDS SSH host key through a trusted channel and store it in
   `SSH_KNOWN_HOSTS`; never disable host verification.
10. Populate and protect the GitHub `production` Environment inputs above.
11. Keep the workflow manual until the first controlled end-to-end deployment
    and recovery exercise succeeds. Enabling an automatic `main` trigger is a
    separate production-integration change and must preserve the exact-SHA CI
    dependency.

## Persistent server state

After deployment, the stable directory contains:

```text
/opt/support-assistant/
├── compose.production.yml       # synchronized from the deployed revision
├── Makefile                     # operational command interface
├── deploy/production.sh         # version-controlled deployment logic
├── .env                         # runtime secret, mode constrained by umask
├── .deployment.env              # proxy topology variables
├── .images.env                  # current deployment-attempt image references
├── .images.last-known-good.env  # most recent fully healthy image references
└── .last-known-good-revision    # corresponding repository revision
```

SQLite data remains in the `support-assistant-data` Docker volume. Redis quota
state is intentionally ephemeral. Pre-migration SQLite backups are stored in
that volume under `/app/data/backups/app.db.before-<backup-id>`; backup IDs are
unique per workflow run and retry.

## Deployment behavior

The workflow writes repository and runtime files only into a per-run staging
directory. It validates the staged Compose definition, prepares all live-file
replacements, and renames each replacement into place on the same filesystem;
an interrupted transfer therefore cannot expose a partially written live file.

The deploy script validates both image references as GHCR digests, pulls the
required images, and starts Redis. It stops the backend, creates and integrity-
checks a unique SQLite backup, and only then runs the one-shot Alembic migration.
It starts backend/frontend with bounded health waits and verifies `/api/health`
through Nginx. GitHub Actions performs a second bounded public check through
`PRODUCTION_URL`; only after that succeeds does it atomically promote the
current image references and revision to last-known-good state.

A failed migration fails deployment and leaves the backend stopped. The script
does not perform an automatic database downgrade or claim that an image rollback
reverses persistent schema/data changes.

Operational commands in the stable directory:

```bash
make production-migrate
make production-health
make production-restore-images
make production-deploy \
  BACKEND_IMAGE=ghcr.io/owner/image@sha256:0000000000000000000000000000000000000000000000000000000000000000 \
  FRONTEND_IMAGE=ghcr.io/owner/image@sha256:0000000000000000000000000000000000000000000000000000000000000000
```

Normal production deployments must come from GitHub Actions, not manual image
selection. The Make targets exist for controlled recovery and diagnostics.

## Recovery boundary

If a migration fails, keep the backend stopped. Identify the matching immutable
backup under `/app/data/backups`, preserve the failed database for diagnosis,
and restore the selected backup only during an explicit maintenance window.
Do not overwrite the live database in place while a backend or migration
container can access it, and never automatically run an Alembic downgrade.

If service replacement fails after a successful migration, first inspect schema
compatibility. When application rollback is safe, run
`make production-restore-images`; this atomically restores
`.images.last-known-good.env` to `.images.env` but deliberately does not change
services. Then validate Compose, update services, and repeat gateway and public
health checks. A failed retry never overwrites last-known-good state; promotion
occurs only after both health layers pass.

The first real deployment belongs to the production-integration phase. Verify
SSH host checking, GHCR access, runtime file ownership, migration behavior,
container health, public routing, deployed digests, and the documented manual
recovery procedure during that controlled deployment.

## Repository-side validation

Without production access, validate the foundation with:

```bash
make deployment-script-test
make check
make verify
make docker-check
```

These commands do not perform SSH deployment or require production secrets.
