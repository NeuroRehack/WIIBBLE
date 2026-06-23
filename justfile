# justfile — common WIIBBLE development tasks

default:
    @just --list

sync:
    uv sync --extra dev --extra analysis
    uv pip install -e .

lint:
    uv run ruff check .

format:
    uv run ruff format .

test:
    uv run pytest

coverage:
    # Uses scoped modules and 80% gate from pyproject.toml [tool.pytest.ini_options]
    uv run pytest -v

coverage-full:
    # Informational report across all of src/ (no fail-under gate)
    uv run pytest --cov=src --cov-report=term-missing --cov-fail-under=0

test-unit:
    uv run pytest -m "not integration"

test-integration:
    uv run pytest -m integration

check:
    uv run pre-commit run --all-files

secrets:
    detect-secrets scan --exclude-files '\.venv/.*|src/code_descriptors_postural_control/.*' > .secrets.baseline

audit:
    uv run pip-audit

mock:
    uv run python -m wiibble --mock

session-report PATH:
    uv run wiibble-session-report {{PATH}} --open
