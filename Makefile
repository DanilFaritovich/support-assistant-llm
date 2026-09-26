.PHONY: backend-check frontend-check backend-integration-test backend-e2e-test \
	test check build docker-build health docker-check verify ci

BACKEND_PYTHON ?= .venv/bin/python

backend-check:
	@$(MAKE) -C backend check PYTHON=$(BACKEND_PYTHON)

frontend-check:
	@$(MAKE) -C frontend check

backend-integration-test:
	@$(MAKE) -C backend test-integration PYTHON=$(BACKEND_PYTHON)

backend-e2e-test:
	@$(MAKE) -C backend test-e2e PYTHON=$(BACKEND_PYTHON)

test:
	@$(MAKE) -C backend test PYTHON=$(BACKEND_PYTHON)
	@$(MAKE) -C frontend test

check: backend-check frontend-check

build:
	@$(MAKE) -C frontend build

docker-build:
	@docker compose config --quiet
	@docker compose build

health:
	@docker compose exec --no-TTY frontend \
		wget -qO- http://127.0.0.1/api/health

docker-check:
	@set -eu; \
	cleanup() { docker compose down; }; \
	trap cleanup EXIT; \
	trap 'exit 130' HUP INT TERM; \
	$(MAKE) docker-build; \
	docker compose up --detach --wait; \
	$(MAKE) health; \
	printf '\n'

verify: backend-integration-test backend-e2e-test build

ci: check verify docker-check
