# WIIBBLE — Development Guide

This document describes how developers should work with WIIBBLE, including setup, testing, building, and contribution flow.

## 1. Development Setup

### Prerequisites
- Windows 10 or 11
- Python 3.8+ (3.11 recommended)
- .NET 8.0 SDK
- .NET Framework 4.8
- Git
- `uv` package manager
- Visual Studio Code or another editor of your choice

### Install dependencies

From the repository root:

```powershell
uv sync
```

To install developer tools including Nuitka:

```powershell
uv sync --extra dev
```

### Virtual environment

`uv sync` creates and manages `.venv` automatically. You can activate it manually if needed:

```powershell
.venv\Scripts\activate
```

## 2. Running the App

### Development mode with hardware

```powershell
uv run python main.py
```

### Development mode without hardware (mock)

```powershell
uv run python main.py --mock --mock-scenario sway
```

Supported mock scenarios:
- `sway`
- `still`
- `lean_left`
- `lean_right`
- `hands`
- `step_on_off`

## 3. Build the C# library

See [SETUP.md](SETUP.md) — Step 4.

## 4. Building a standalone executable

See [SETUP.md](SETUP.md) — Step 8.

## 5. Logging and debugging

WIIBBLE uses Python's standard `logging` module. Logs are written to:

```text
%USERPROFILE%\.wiibble\wiibble.log
```

The app also logs to stdout in normal development runs.

## 6. Code formatting and linting

Ruff is configured in `pyproject.toml` (rules: E, F, W, I; `line-length = 100`).

```powershell
# Check for violations
uv run ruff check .

# Auto-fix safe violations
uv run ruff check . --fix

# Verify formatting
uv run ruff format --check .

# Apply formatting
uv run ruff format .
```

## 7. Tests

Tests live in `tests/` and use `pytest` with `pytest-cov`. Run them with:

```powershell
uv run pytest -v
```

Coverage is measured over `data_processing.py`, `state.py`, and `recording.py`. A minimum of **80%** total coverage is enforced — the test run will fail if it drops below.

Current coverage: **82%** (63 tests).

| Module | Coverage |
|---|---|
| `recording.py` | 100% |
| `state.py` | 98% |
| `data_processing.py` | 55% (hardware paths excluded) |

> Hardware-coupled modules (`app.py`, `ui.py`, `board_connection.py`, etc.) are excluded from coverage measurement. Use `--mock` mode to smoke-test the full app.

## 8. CI

GitHub Actions runs automatically on push to `develop`/`main` and on PRs to `main`.

Two jobs defined in `.github/workflows/ci.yml`:

| Job | What it does |
|---|---|
| `lint` | `ruff check .` + `ruff format --check .` |
| `test` | `pytest -v` with coverage gate (≥80%) |

`test` only runs after `lint` passes. Both jobs run on `windows-latest`.

## 9. Contribution workflow

1. Create a feature branch from `develop`.
2. Make small, testable changes.
3. Keep the code style consistent with the existing repository.
4. Update documentation when adding or changing functionality.
5. Open a pull request describing the change and how to reproduce it.

## 9. Useful commands

- Run app in mock mode:
  ```powershell
  uv run python main.py --mock --mock-scenario sway
  ```
- Build exe:
  ```powershell
  .\compiler.bat
  ```
- Build C# library:
  ```powershell
  cd WiiBalanceBoardLibrary
  dotnet build
  cd ..
  ```
- Refresh dependencies:
  ```powershell
  uv sync
  uv sync --extra dev
  ```
