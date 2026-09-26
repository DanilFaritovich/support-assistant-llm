.PHONY: backend-fix frontend-fix fix backend-check frontend-check \
	backend-integration-test backend-e2e-test test check build docker-build health \
	edge-rate-limit-smoke docker-check verify ci

BACKEND_PYTHON ?= .venv/bin/python

backend-fix:
	@$(MAKE) -C backend fix PYTHON=$(BACKEND_PYTHON)

frontend-fix:
	@$(MAKE) -C frontend fix

fix: backend-fix frontend-fix

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

edge-rate-limit-smoke:
	@docker compose exec --no-TTY frontend sh -ec '\
		limited=0; \
		i=0; \
		while [ $$i -lt 30 ]; do \
			i=$$((i + 1)); \
			response=$$(wget -S -O /dev/null http://127.0.0.1/api/health 2>&1 || true); \
			case "$$response" in \
				*"429 Too Many Requests"*) limited=1; break ;; \
			esac; \
		done; \
		test $$limited -eq 1'

docker-check:
	@set -eu; \
	cleanup() { docker compose down; }; \
	trap cleanup EXIT; \
	trap 'exit 130' HUP INT TERM; \
	$(MAKE) docker-build; \
	docker compose up --detach --wait; \
	$(MAKE) health; \
	$(MAKE) edge-rate-limit-smoke; \
	printf '\n'

verify: backend-integration-test backend-e2e-test build

ci: check verify docker-check
