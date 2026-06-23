# WIIBBLE — Developer Setup

This guide covers environment setup, development workflow, packaging, and CI for WIIBBLE. For contribution guidelines see [CONTRIBUTING.md](../../CONTRIBUTING.md). For interface usage see [User Manual](../user/manual.md).

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Environment Setup](#2-environment-setup)
3. [Running the App](#3-running-the-app)
   - [Linux development (mock mode)](#linux-development-mock-mode)
4. [Development Workflow](#4-development-workflow)
5. [Posturographic Analysis and Reporting](#5-posturographic-analysis-and-reporting)
6. [Packaging and Building](#6-packaging-and-building)
7. [Troubleshooting](#7-troubleshooting)
8. [Key Files and Directory Layout](#8-key-files-and-directory-layout)
9. [Useful Commands Recap](#9-useful-commands-recap)

---

## 1. Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Windows | 10 or 11 | Required for Bluetooth HID and DearPyGui viewport |
| Python | 3.11 or 3.12 | **3.14 unsupported**; [python.org](https://www.python.org/downloads/) |
| .NET 8.0 SDK | Latest | [dotnet.microsoft.com](https://dotnet.microsoft.com/en-us/download) |
| .NET Framework | 4.8 | Usually pre-installed on Win 10/11. Verify: `reg query "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full" /v Release` |
| Git | Any recent | [git-scm.com](https://git-scm.com/) |
| uv | Latest | Python dependency manager; replaces pip |
| just | Latest | Task runner for lint, test, format (`just --list`) |
| Bluetooth adapter | Built-in or USB | For real board only, not needed in mock mode |

---

## 2. Environment Setup

> **Why uv?** uv resolves and installs all dependencies in seconds, manages the virtual environment automatically, and produces a lockfile (`uv.lock`) for reproducibility.

### (a) Install uv and just

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
uv --version
```

Install [just](https://github.com/casey/just) for your platform, then verify with `just --version`.

### (b) Clone the repository

```powershell
git clone https://github.com/NeuroRehack/WIIBBLE.git
cd WIIBBLE
git checkout develop
```

### (c) Create a Python 3.12 virtual environment and install dependencies

Ensure Python 3.12 is installed. Check with:

```powershell
python --version
# Or specify path:
uv venv --python=python3.12
```

Then install dependencies and set up as a package:

```powershell
just sync
# equivalent to:
# uv sync --extra dev
# uv pip install -e .
```

This creates `.venv/` in the project directory. You can activate manually with:

```powershell
.venv\Scripts\activate
```

Most `uv run` and `just` commands detect the venv automatically.

Optional: copy `.env.example` to `.env` if you need to override `WIIBBLE_SETTINGS_PATH` for local testing.

### (d) Build the C# board library

Required for real hardware; not needed in mock mode.

```powershell
cd WiiBalanceBoardLibrary
dotnet build
cd ..
```

Success output ends with: `Build succeeded. 0 Warning(s) 0 Error(s)`

The DLL is placed at `WiiBalanceBoardLibrary/bin/Debug/net48/WiiBalanceBoardLibrary.dll` and loaded automatically by the app.

### (e) Verify setup with mock mode

```powershell
uv run python -m wiibble --mock --mock-scenario sway
```

The app should launch, show the tare screen, then the main screen with a moving cursor. If this works, the environment is correctly set up.

### (f) Pair the Wii Balance Board (real hardware only)

See [User Manual — Board Pairing](../user/manual.md#board-pairing) for the full pairing procedure and MAC address cases.

### (g) Run with real hardware

Once the board is paired and the LED is blinking blue:

```powershell
uv run python -m wiibble
```

---

## 3. Running the App

| Command | Description |
|---|---|
| `uv run python -m wiibble` | Run with real board |
| `uv run python -m wiibble --mock` | Run with simulated board (default scenario: sway) |
| `uv run python -m wiibble --mock --mock-scenario lean_left` | Run with specific mock scenario |

Available mock scenarios: `sway`, `still`, `lean_left`, `lean_right`, `hands`, `step_on_off`, `calibration`.

For interface usage, controls, and recording instructions see [User Manual](../user/manual.md).

### Linux development (mock mode)

You can develop and test UI features on Linux using mock mode. Real hardware, the C# DLL (`dotnet build`), and the Nuitka installer remain **Windows-only**.

**Prerequisites**

- Python 3.11 or 3.12, `uv`, `just`, and dev dependencies (`just sync`)
- A display server (local desktop), or headless via `xvfb-run` for automated smoke tests

**Run mock UI**

```bash
uv run python -m wiibble --mock --mock-scenario sway
```

The app should show the tare screen, then the main canvas with a simulated swaying cursor.

To test on-board calibration without hardware:

```bash
uv run python -m wiibble --mock --mock-scenario calibration
```

Open **Settings → Cal scale** to test board scale calibration (set board reference to e.g. 20 kg).

**What works on Linux**

| Task | Command |
|---|---|
| Mock UI (calibration, canvas, settings panel) | `uv run python -m wiibble --mock` |
| Unit tests | `just test` |
| Offline analysis | `uv run wiibble-process-recordings …` |
| HTML reports | `uv run wiibble-report …` |

**What does not work on Linux**

- Real Wii Balance Board (Bluetooth pairing + C# handshake)
- Building or running `WIIBBLE.exe` / the Inno Setup installer

Logs are written to `~/.wiibble/wiibble.log` and stdout.

---

## 4. Development Workflow

Use `just` as the primary entry point for quality checks. Run `just` or `just --list` to see all targets.

| Target | Description |
|---|---|
| `just sync` | Install dev dependencies and editable package |
| `just lint` | Ruff lint |
| `just format` | Ruff format |
| `just test` | Run pytest |
| `just coverage` | Pytest with coverage report |
| `just check` | Pre-commit hooks on all files |
| `just audit` | Scan dependencies for known CVEs (`pip-audit`) |

Install pre-commit hooks once after cloning:

```powershell
pre-commit install
pre-commit install --hook-type commit-msg
```

### Logging

Logs are written to `%USERPROFILE%\.wiibble\wiibble.log` and stdout.

- `DEBUG` — raw sensor data
- `INFO` — state transitions
- `ERROR` — failures

### Code formatting and linting

[Ruff](https://github.com/astral-sh/ruff) is configured in `pyproject.toml`:

```powershell
just lint
just format
# or directly:
uv run ruff check .
uv run ruff format .
```

CI rejects PRs that fail either check.

### Tests

Tests live in `tests/` and use `pytest` + `pytest-cov`. A coverage gate of **≥ 80%** is enforced for `wiibble/features/data_processing.py`, `wiibble/utils/state.py`, and `wiibble/board/recording.py`. Hardware-dependent and UI code is excluded from the gate.

```powershell
just test
# or: uv run pytest -v
```

Current coverage (last verified locally):

| Module | Coverage |
|---|---|
| `wiibble/board/recording.py` | 93% |
| `wiibble/utils/state.py` | 96% |
| `wiibble/features/data_processing.py` | 83% |
| **Total (gated modules)** | **91%** |

Use `MockHIDDevice` from `wiibble/board/mock_board.py` for any test that touches the sensor pipeline. Never write tests that require a physical board.

### Continuous integration

GitHub Actions: `.github/workflows/ci.yml`

| Job | What it does |
|---|---|
| `lint` | `ruff check .` and `ruff format --check .` |
| `test` | `pytest -v` with ≥ 80% coverage gate (runs after lint passes) |

Both jobs run on `windows-latest`.

Pending CI additions: `dotnet build` job, Nuitka executable artifact, see [TODO.md](TODO.md).

---

## 5. Posturographic Analysis and Reporting

Analysis and reporting run **offline**, outside the compiled app. This keeps the Nuitka build fast and free of heavy dependencies.

### Install analysis dependencies

The `analysis` extra provides scipy (signal processing for the vendored descriptor library), plotly, and jinja2 (HTML reports):

```powershell
uv sync --extra analysis
```

For development (lint, tests, Nuitka), use `just sync`, which installs `dev` and `analysis` extras together.

### Analyse recordings

Both offline CLIs scan the **configured recordings folder** — the same path as **Save Location** in the app (`recording_dir` in the user settings file). When unset, the default is `~/Documents/WIIBBLE/recordings`.

Process all new (unanalysed) recordings in that folder:

```powershell
uv run wiibble-process-recordings --new
```

Process a specific recording (path can be anywhere):

```powershell
uv run wiibble-process-recordings "C:\Users\...\recording_YYYYMMDD_HHMMSS.csv"
```

Re-analyse and overwrite all recordings in the configured folder:

```powershell
uv run wiibble-process-recordings --all
```

**Output:** `features_YYYYMMDD_HHMMSS.json` written alongside each CSV — ~80–90 posturographic features plus provenance metadata.

**Minimum duration:** Recordings shorter than 20 s are skipped.

For a full technical breakdown of each analysis step see [DATA_PIPELINE.md](DATA_PIPELINE.md).

### Generate HTML reports

Batch mode (uses the configured recordings folder; auto-detects features JSON and writes HTML next to each CSV):

```powershell
uv run wiibble-report --new
uv run wiibble-report --all
```

- `--new` — generate reports only for CSVs that do not yet have a matching `report_<timestamp>.html`
- `--all` — regenerate reports for every CSV in the folder

Single recording:

```powershell
uv run wiibble-report "C:\Users\...\recording_YYYYMMDD_HHMMSS.csv"
```

Explicit paths (single-file mode only; cannot be combined with `--new` or `--all`):

```powershell
uv run wiibble-report path\to\recording.csv `
    --features path\to\features.json `
    --out path\to\report.html
```

Omit `--out` to write `report_<timestamp>.html` next to the CSV. Omit `--features` for automatic search of the matching JSON. If no features JSON is found, a partial report is generated.

The report contains: sway path + 95% confidence ellipse, ML/AP time series, velocity, power spectral density, diffusion plot, spatial density, and feature summary table. All captions are strictly descriptive, no clinical interpretation.

To customise report figures or layout, edit `src/wiibble/cli/report.py` and the `_HTML_TEMPLATE` Jinja2 template. See [VISUALISATION_REFERENCES.md](VISUALISATION_REFERENCES.md) for the literature justification of each figure.

**Dependencies:** Plotly, Jinja2, included in the `analysis` extras group.

---

## 6. Packaging and Building

### Build the standalone executable

Requires `uv sync --extra dev`:

```powershell
.\compiler.bat
```

Output: `dist_nuitka/wiibble.dist/WIIBBLE.exe`

Test the build in mock mode before distributing:

```powershell
dist_nuitka\wiibble.dist\WIIBBLE.exe --mock --mock-scenario sway
```

### Create the installer (for clinic distribution)

Requires [Inno Setup 6](https://jrsoftware.org/isinfo.php) with `iscc` on `PATH`. `compiler.bat` calls `iscc installer.iss` automatically if it is available.

Manual:

```powershell
iscc installer.iss
```

Output: `installer_output/WIIBBLE-<version>-Setup.exe`

Supports `/SILENT` and `/VERYSILENT` flags for managed deployment.

### Non-obvious build requirements

- **Windows only.** DearPyGui's `viewport_drawlist`, `ctypes.windll`, and the C# DLL are all Windows-specific.
- **.NET Framework 4.8** must be present to build and run the C# DLL. Pre-installed on Windows 10/11; may be absent on server SKUs.
- **Bluetooth pairing is separate from the app.** The board must be paired in Windows Bluetooth settings before launching.
- **Settings are per-user.** On Windows: `%APPDATA%\WIIBBLE\settings.json`; on Linux/macOS: `~/.wiibble/settings.json`. The recording save location (`recording_dir`) is shared by the app and offline CLI batch commands; default is `~/Documents/WIIBBLE/recordings`.

---

## 7. Troubleshooting

| Problem | Solution |
|---|---|
| DLL error on launch | Confirm `dotnet build` succeeded. Check .NET Framework 4.8 is installed. |
| `uv sync` fails | Ensure Python 3.11 or 3.12 is installed and on PATH. Try `uv python install 3.11`. |
| Board not found | Bluetooth must be on, board paired, LED blinking blue. Try re-pairing. Check battery. |
| Black screen / no canvas | Restart the app. Update graphics drivers if persistent. |
| Settings reset needed | Delete `%APPDATA%\WIIBBLE\settings.json` (Windows) or `~/.wiibble/settings.json` (Linux/macOS); recreated automatically on next launch. |
| Analysis error (missing packages) | Run `uv sync --extra analysis`. |

---

## 8. Key Files and Directory Layout

```
WIIBBLE/
├── src/
│   └── wiibble/
│       ├── __main__.py            # App entry point (`python -m wiibble` / `wiibble` CLI)
│       ├── app.py                 # Session lifecycle, main loop
│       ├── analysis/              # CoP feature extraction, calibration
│       ├── board/                 # Board connection, mock board, CSV recording
│       ├── features/              # Sensor data processing pipeline
│       ├── ui/                    # Rendering, theme, input handlers
│       ├── cli/
│       │   ├── process_recordings.py  # `wiibble-process-recordings` entrypoint
│       │   ├── recordings_dir.py      # shared recordings-folder helper for CLIs
│       │   └── report.py              # `wiibble-report` entrypoint
│       └── utils/                 # Constants, state, resources
├── WiiBalanceBoardLibrary/      # C# project (build to produce DLL)
├── tests/                       # pytest test suite
├── docs/
│   ├── dev/
│   │   ├── setup.md             # this file
│   │   ├── architecture.md
│   │   ├── DATA_PIPELINE.md
│   │   ├── VISUALISATION_REFERENCES.md
│   │   ├── TODO.md
│   │   └── decisions/
│   │       └── 001-migrate-to-pyqt6.md
│   └── user/
│       └── manual.md
├── justfile
├── CHANGELOG.md
└── CONTRIBUTING.md
```

---

## 9. Useful Commands Recap

```powershell
# Run
uv run python -m wiibble --mock --mock-scenario sway
uv run python -m wiibble

# Build C# library
cd WiiBalanceBoardLibrary && dotnet build && cd ..

# Quality (prefer just targets)
just lint
just format
just test
just coverage
just check

# Analysis and reporting
uv run wiibble-process-recordings --new
uv run wiibble-report --new

# Build executable
.\compiler.bat

# Dependency management
just sync
uv sync --extra analysis

# Reset user preferences (Windows)
del "%APPDATA%\WIIBBLE\settings.json"
```
