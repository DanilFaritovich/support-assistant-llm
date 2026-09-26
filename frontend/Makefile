.PHONY: all install fix lint format-check typecheck test-unit test build check

all: check build

install:
	@npm ci

fix:
	@npm run lint:fix
	@npm run format

lint:
	@npm run lint

format-check:
	@npm run format:check

typecheck:
	@npm run typecheck

test-unit: test

test:
	@npm run test

build:
	@npm run build

check:
	@npm run check
