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

## 5. Building the physio installer

WIIBBLE ships to clinical machines as a standard Windows installer (`.exe`) produced by [Inno Setup 6](https://jrsoftware.org/isinfo.php).

### Prerequisites

1. Run `compiler.bat` first to produce `dist_nuitka/main.dist/`.
2. Install Inno Setup 6.x and ensure `iscc` is on your `PATH`.

### Build

`compiler.bat` calls `iscc` automatically after the Nuitka step if it is found on `PATH`:

```powershell
.\compiler.bat
```

Or build the installer separately (after Nuitka has already run):

```powershell
iscc installer.iss
```

Output: `installer_output\WIIBBLE-0.1.0-Setup.exe`

### Deployment

The installer supports silent/managed deployment:

```powershell
# Silent (progress bar, no prompts)
WIIBBLE-0.1.0-Setup.exe /SILENT

# Fully silent (no UI at all — for SCCM / Intune)
WIIBBLE-0.1.0-Setup.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
```

Installs to `%ProgramFiles%\WIIBBLE\`. Creates a Start Menu entry and an optional Desktop shortcut. A standard uninstaller is registered in Add/Remove Programs.

> Patient recordings are saved to `%USERPROFILE%\.wiibble\recordings\` and are **never** touched by the uninstaller.

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

Current coverage: **80.56%** (70 tests).

| Module | Coverage |
|---|---|
| `recording.py` | 95% |
| `state.py` | 98% |
| `data_processing.py` | 53% (hardware paths excluded) |

> Hardware-coupled modules (`app.py`, `ui.py`, `board_connection.py`, etc.) are excluded from coverage measurement. Use `--mock` mode to smoke-test the full app.

## 8. CI

GitHub Actions runs automatically on push to `develop`/`main` and on PRs to `main`.

Two jobs defined in `.github/workflows/ci.yml`:

| Job | What it does |
|---|---|
| `lint` | `ruff check .` + `ruff format --check .` |
| `test` | `pytest -v` with coverage gate (≥80%) |

`test` only runs after `lint` passes. Both jobs run on `windows-latest`.

## 9. Posturographic Analysis

The analysis pipeline (`analysis.py`, `process_recordings.py`) depends on
`pandas`, `scikit-learn`, and `statsmodels`. These are **not** compiled into the
clinical executable (they make Nuitka builds extremely slow). Instead, run analysis
offline on a workstation after a session.

### Install analysis extras

```powershell
uv sync --extra analysis
```

### Process recordings

```powershell
# Process all unanalysed CSVs in recordings/ (skips existing JSON sidecars)
python process_recordings.py --new

# Process specific file(s)
python process_recordings.py recordings/recording_20260325_211625.csv

# Reprocess everything, overwriting existing JSON sidecars
python process_recordings.py --all
```

Output JSON files are written alongside each CSV:
`recordings/features_YYYYMMDD_HHMMSS.json`

See [DATA_PIPELINE.md](DATA_PIPELINE.md) for the full feature-extraction pipeline.

## 10. Contribution workflow

1. Create a feature branch from `develop`.
2. Make small, testable changes.
3. Keep the code style consistent with the existing repository.
4. Update documentation when adding or changing functionality.
5. Open a pull request describing the change and how to reproduce it.

## 11. Useful commands

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
