.PHONY: fmt lint typecheck test check

PY := .venv/bin/python

fmt:
	.venv/bin/ruff format .
	.venv/bin/ruff check --fix .

lint:
	.venv/bin/ruff check .
	.venv/bin/ruff format --check .

typecheck:
	.venv/bin/mypy

test:
	$(PY) -m pytest

check: lint typecheck test