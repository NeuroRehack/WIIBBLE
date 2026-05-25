# WIIBBLE — Developer Setup & Workflow Guide

This unified guide covers setup, usage, development workflow, packaging, troubleshooting, and contribution for WIIBBLE. Both new users and developers should start here.

---

## 1. Prerequisites

| Requirement         | Version           | Notes                                            |
|--------------------|-------------------|--------------------------------------------------|
| Windows            | 10 or 11          | Required for Bluetooth HID                       |
| Python             | 3.11 or 3.12      | **3.14 unsupported**; [python.org](https://www.python.org/downloads/) |
| .NET 8.0 SDK       | Latest            | [dotnet.microsoft.com](https://dotnet.microsoft.com/en-us/download) |
| .NET Framework     | 4.8               | Usually present in Win 10/11. Check: `reg query "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full" /v Release` |
| Git                | Any recent        | [git-scm.com](https://git-scm.com/)              |
| uv                 | Latest            | Python dep manager; replaces pip                  |
| Bluetooth adapter  | Built-in or USB   | For Wii Board; see **Pairing** below             |

---

## 2. Environment Setup (Windows)

> **Why uv?** uv is a fast drop-in pip replacement that resolves and installs all dependencies in seconds, handles virtual environments automatically, and generates a lockfile (`uv.lock`) for pinned reproducibility.

### (a) Install uv

Open a PowerShell terminal and run:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
uv --version   # You should see something like 'uv 0.x.x'
```

### (b) Clone the Repository

```powershell
git clone https://github.com/NeuroRehack/WIIBBLE.git
cd WIIBBLE
git checkout develop
```

### (c) Install Python Dependencies

```powershell
uv sync
```

- Creates `.venv/` in the project directory
- Installs all runtime dependencies from `pyproject.toml`
- Writes `uv.lock`

To install dev tools (lint, build, test, package):

```powershell
uv sync --extra dev
```

> **Note:** You do not need to activate the virtual environment manually. All `uv run` commands use it. To activate interactively:
>
> ```powershell
> .venv\Scripts\activate
> ```

### (d) Build the C# Board Library

```powershell
cd WiiBalanceBoardLibrary
dotnet build
cd ..
```
- Success looks like:
  > Build succeeded.\n    0 Warning(s)\n    0 Error(s)
- DLL is placed in `WiiBalanceBoardLibrary/bin/Debug/net48/WiiBalanceBoardLibrary.dll`. Used automatically by the app.

### (e) Verify Setup With Mock Mode

Before connecting hardware, confirm the app runs with simulated data:

```powershell
uv run python main.py --mock --mock-scenario sway
```

- App should launch and show calibration and main screens, cursor moving in a sway pattern.
- Other scenarios:
   ```powershell
   uv run python main.py --mock --mock-scenario still
   uv run python main.py --mock --mock-scenario lean_left
   uv run python main.py --mock --mock-scenario lean_right
   uv run python main.py --mock --mock-scenario hands
   uv run python main.py --mock --mock-scenario step_on_off
   ```

### (f) Pair the Wii Balance Board (Bluetooth)

See the **Board Pairing** section in the `ReadMe.md` for detailed instructions and troubleshooting. In brief:

- Find your Bluetooth MAC address with `getmac /v /fo list`.
- If address **does NOT contain "00"**: Use WiiBalanceWalker v0.5 to permanently pair using generated PIN (see ReadMe).
- If address **contains "00"**: Pair via `Control Panel > Hardware and Sound > Devices and Printers` *for each session* (cannot be permanently paired).

### (g) Run With Real Hardware

1. Ensure the board is paired and blue LED is blinking.
2. Run:

   ```powershell
   uv run python main.py
   ```

---

## 3. Application Usage & Controls

- See [USER_MANUAL.md](USER_MANUAL.md) for interface, canvas, settings.
- Command-line flags: `--mock`, `--mock-scenario sway|still|lean_left|lean_right|hands|step_on_off`

---

## 4. Packaging, Building, and Installer

### (a) Build Standalone Executable (optional)

Requires `uv sync --extra dev` (for Nuitka and tools):

```powershell
.\compiler.bat
```
- Output: `outputBuild/WIIBBLE/WIIBBLE.exe`
- Run with hardware or use mock mode:
   ```powershell
   outputBuild\WIIBBLE\WIIBBLE.exe --mock --mock-scenario sway
   ```

### (b) Create Installer (optional; clinics)

Requires [Inno Setup 6](https://jrsoftware.org/isinfo.php):
- `compiler.bat` auto-calls `iscc installer.iss` if `iscc` is in `PATH`.
- Manual: `iscc installer.iss`
- Output: `installer_output/WIIBBLE-<version>-Setup.exe`
- Supports `/SILENT` or `/VERYSILENT` flags for managed install/uninstall.

---

## 5. Troubleshooting

**App crashes with DLL error:** Confirm you ran `dotnet build`. Check that `.NET Framework 4.8` is installed.

**`uv sync` fails:** Make sure Python 3.11 or 3.12 is installed and on PATH. Try `uv python install 3.11` to let `uv` set up its own Python.

**Board not found:** Bluetooth must be enabled, board paired, and LED blinking blue. Try re-pairing; check battery level.

**Black screen/no canvas:** Try restarting the app. Update your graphics drivers if persistent.

**Settings file issues/reset:**
- User preferences stored in `.wiibble/settings.json` under your user profile.
- To reset all settings to defaults, delete this file — it is recreated automatically on app restart.

---

## 6. File Structure (Key Files/Dirs)

```
WIIBBLE/
├── main.py                  # Entry point
├── app.py                   # Session lifecycle, main loop
├── ui.py                    # Canvas, screen rendering
├── input.py                 # Mouse, canvas interaction
├── theme.py                 # Colours, fonts
├── data_processing.py       # Sensor & coordinate pipeline
├── calibration.py           # Calibration/tare logic
├── state.py                 # AppState, Settings dataclasses
├── constants.py             # Hardware constants
├── resources.py             # Path resolution
├── mock_board.py            # Hardware simulator for dev/testing
├── board_connection.py      # C# DLL bridge (Bluetooth handshake)
├── WiiBalanceBoardLibrary/  # C# project (build for DLL)
├── pyproject.toml           # Dependencies, tooling config
├── ReadMe.md                # Project entrypoint, pairing help
```

---

## 7. Development Workflow

### (a) Logging
- Logs in `%USERPROFILE%\.wiibble\wiibble.log` and stdout.

### (b) Code Formatting and Linting
- [Ruff](https://github.com/astral-sh/ruff) config in `pyproject.toml`:
   ```powershell
   uv run ruff check .
   uv run ruff check . --fix       # Safe autofix
   uv run ruff format --check .    # Verify formatting
   uv run ruff format .            # Apply formatting
   ```

### (c) Tests
- Tests in `tests/`, use `pytest` + `pytest-cov`.
- Enforced **≥80%** coverage for `data_processing.py`, `state.py`, `recording.py` (hardware UI code not counted).
   ```powershell
   uv run pytest -v
   ```
- Typical modules covered:
   | Module            | Coverage |
   |-------------------|----------|
   | `recording.py`    | 95%      |
   | `state.py`        | 98%      |
   | `data_processing` | ~53%     |

### (d) Continuous Integration (CI)
- GitHub Actions: `.github/workflows/ci.yml`
- Two jobs:
   | Job   | What it does                                              |
   |-------|----------------------------------------------------------|
   | lint  | `ruff check .` & `ruff format --check .`                 |
   | test  | `pytest -v` with ≥80% coverage gate (after lint passes)  |
- Both run on `windows-latest`.

### (e) devPosturographic Analysis Tools


- For offline analysis of recorded CSVs: `analysis.py`, `process_recordings.py`
- Install extras:
   ```powershell
   uv sync --extra analysis
   ```
- For user-facing step-by-step instructions (commands, output), see the “Posturographic Analysis” section in [USER_MANUAL.md](USER_MANUAL.md).
- See [DATA_PIPELINE.md](DATA_PIPELINE.md) for the feature extraction pipeline details.

## Report Generation (HTML, Plotly)

This is the canonical reference for session report generation in WIIBBLE.

- **Purpose:**  
  - `report.py` produces a self-contained, interactive HTML report with all posturography plots and features from a single session.
- **How it works:**
  - Needs a CSV and matching features JSON (see Data Pipeline).
  - Jinja2 template and Plotly generate all figures and captions.
  - Captions are strictly descriptive (not interpretive/clinical).
- **How to run:**
  ```powershell
  uv run python report.py recordings/recording_YYYYMMDD_HHMMSS.csv --features recordings/features_YYYYMMDD_HHMMSS.json --out recordings/report_YYYYMMDD_HHMMSS.html
  ```
  - Omit `--out` for default output.
- **Customizing:**  
  - Edit `report.py` (charts, table, captions) or `_HTML_TEMPLATE` (layout).
  - See `VISUALISATION_REFERENCES.md` for design/literature justifications.
- **Dependencies:**  
  - Plotly, Jinja2 — included in main/analysis extras, see `pyproject.toml`.

For user and workflow context, cross-reference [Data Pipeline](DATA_PIPELINE.md#9-report-generation) or [User Manual](USER_MANUAL.md#session-reports-html).

---

## 8. Contribution Workflow

1. Create a feature branch from `develop`.
2. Make small, testable, well-linted changes.
3. Keep the code style consistent.
4. Update documentation when adding or changing functionality.
5. Open a pull request with clear description and steps to reproduce.

---

## 9. Useful Commands Recap

- **Run with mock scenario:**
  ```powershell
  uv run python main.py --mock --mock-scenario sway
  ```
- **Run with board:**
  ```powershell
  uv run python main.py
  ```
- **Build C# library:**
  ```powershell
  cd WiiBalanceBoardLibrary
  dotnet build
  cd ..
  ```
- **Build executable:**
  ```powershell
  .\compiler.bat
  ```
- **Update dependencies:**
  ```powershell
  uv sync
  uv sync --extra dev
  ```
- **Reset all preferences:**
  Delete `.wiibble/settings.json`
