# justfile — common WIIBBLE development tasks

default:
    @just --list

sync:
    uv sync --extra dev
    uv pip install -e .

lint:
    uv run ruff check .

format:
    uv run ruff format .

test:
    uv run pytest

coverage:
    uv run pytest --cov=src --cov-report=term-missing

test-unit:
    uv run pytest -m "not integration"

test-integration:
    uv run pytest -m integration

check:
    pre-commit run --all-files

secrets:
    detect-secrets scan --exclude-files '\.venv/.*|src/code_descriptors_postural_control/.*' > .secrets.baseline

audit:
    uv run pip-audit

mock:
    uv run python -m wiibble --mock
