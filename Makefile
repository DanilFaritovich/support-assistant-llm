.PHONY: backend-check frontend-check build docker-check check ci

BACKEND_PYTHON ?= .venv/bin/python

backend-check:
	$(MAKE) -C backend check PYTHON=$(BACKEND_PYTHON)

frontend-check:
	$(MAKE) -C frontend check

build:
	$(MAKE) -C frontend build

docker-check:
	@set -eu; \
	cleanup() { docker compose down; }; \
	trap cleanup EXIT; \
	trap 'exit 130' HUP INT TERM; \
	docker compose config --quiet; \
	docker compose build; \
	docker compose up --detach --wait; \
	docker compose exec --no-TTY frontend \
		wget -qO- http://127.0.0.1/api/health; \
	printf '\n'

check: backend-check frontend-check build

ci: check docker-check
