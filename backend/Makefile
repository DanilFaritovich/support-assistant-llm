
.PHONY: check lint format format-check typecheck test-unit test-integration test-e2e test fix

PYTHON ?= python
PYTEST_FLAGS ?= -q --tb=short

# Run fast checks used during regular development
check: lint format-check typecheck test-unit

# Check code quality
lint:
	@$(PYTHON) -m ruff check .

# Check code formatting
format: format-check

format-check:
	@$(PYTHON) -m ruff format --check .

# Run static type checking
typecheck:
	@$(PYTHON) -m mypy app

# Run tests by scope
test-unit:
	@$(PYTHON) -m pytest $(PYTEST_FLAGS) tests/unit

test-integration:
	@$(PYTHON) -m pytest $(PYTEST_FLAGS) tests/integration

test-e2e:
	@$(PYTHON) -m pytest $(PYTEST_FLAGS) tests/e2e

test: test-unit test-integration test-e2e

# Automatically fix linting and formatting issues
fix:
	@$(PYTHON) -m ruff check . --fix
	@$(PYTHON) -m ruff format .
