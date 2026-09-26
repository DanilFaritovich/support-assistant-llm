# Project verification

Use the repository Makefiles as the primary verification interface. Do not
duplicate their underlying Ruff, mypy, pytest, npm, or Docker commands in CI.

- `make check` runs the regular backend and frontend checks plus the frontend
  production build.
- `make ci` runs `make check` and the Docker Compose smoke-check.
- `make backend-check`, `make frontend-check`, `make build`, and
  `make docker-check` may be used for a scoped verification run.

The backend implementation remains in `backend/Makefile`. The frontend
Makefile is a thin wrapper around the scripts in `frontend/package.json`.
