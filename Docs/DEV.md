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

Run the formatter/linter via `uv` if configured:

```powershell
uv run ruff check .
```

If `ruff` is installed through `uv sync --extra dev`, it will use the repo's `pyproject.toml` configuration.

## 7. Tests

There are no tests yet in the repository. When tests are added, use:

```powershell
uv run pytest
```

## 8. Contribution workflow

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
