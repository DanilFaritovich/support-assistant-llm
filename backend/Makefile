
.PHONY: check lint format typecheck test fix

PYTHON ?= python

# Run all CI checks
check: lint format typecheck test

# Check code quality
lint:
	$(PYTHON) -m ruff check .

# Check code formatting
format:
	$(PYTHON) -m ruff format --check .

# Run static type checking
typecheck:
	$(PYTHON) -m mypy app

# Run tests
test:
	$(PYTHON) -m pytest -v tests/

# Automatically fix linting and formatting issues
fix:
	$(PYTHON) -m ruff check . --fix
	$(PYTHON) -m ruff format .
