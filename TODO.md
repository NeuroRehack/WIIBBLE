# WIIBBLE — TODO & Roadmap

> Last updated: 2026-03-21  
> This document tracks both **stakeholder feature requests** and **technical/developer recommendations** identified during code review and dev environment setup.

---

## Table of Contents

- [Stakeholder Feature Requests](#-stakeholder-feature-requests)
- [Technical Recommendations](#-technical-recommendations)
  - [Critical Bugs](#-critical-bugs)
  - [Code Quality](#-code-quality)
  - [Developer Experience](#-developer-experience)
  - [Project Structure](#-project-structure)
- [Notes for Development Without Hardware](#-notes-for-development-without-hardware)

---

## 🩺 Stakeholder Feature Requests

> Source: Physiotherapist feedback (received March 2026). These are clinical UX requests from the rehabilitation team at Princess Alexandra Hospital.

### S1 — Cursor Type Toggle
**Priority:** High  
**Feasibility without hardware:** ✅ Yes — pure UI change

Toggle between cursor types (e.g. the current person avatar vs. a simple coloured circle) when the user clicks on the cursor itself. Avoids the need for a menu.

- [ ] Add a `cursor_mode` state variable (`"avatar"` | `"circle"`)
- [ ] On cursor click, toggle between modes
- [ ] Render a plain coloured circle when in simple mode
- [ ] Persist preference across sessions (optional, later)

---

### S2 — Adjustable Trail Length
**Priority:** High  
**Feasibility without hardware:** ✅ Yes — pure UI change

Some patients find the motion trail distracting. Allow reducing or disabling it.

- [ ] Add a slider or small UI control for trail length (number of historical points shown)
- [ ] Range: 0 (no trail) to 100 (current default)
- [ ] Hook into the `historical_coords` list size
- [ ] Consider persisting last-used value

---

### S3 — Zoom / Display Scale Control
**Priority:** High  
**Feasibility without hardware:** ✅ Yes — coordinate scaling change

The current scale is derived from body weight at calibration. Clinicians need to zoom in for low-mobility patients, or zoom out when using hands instead of feet.

- [ ] Add zoom in / zoom out controls (buttons or scroll wheel)
- [ ] Apply a `zoom_factor` multiplier to the `calculate_coordinates()` output
- [ ] Display current zoom level on screen
- [ ] Allow resetting zoom to the auto-calibrated default
- [ ] Consider a zoom range of 0.25× to 4×

---

### S4 — Moving Average Filter with Adjustable Window Size
**Priority:** High  
**Feasibility without hardware:** ✅ Yes — signal processing, testable with mock data

Add a smoothing filter to reduce noise in the force sensor signal. Window size must be adjustable live during a session so clinicians can experiment with participants.

- [ ] Implement a moving average filter over the raw corner sensor values
- [ ] Add a small on-screen text field or slider to set the window size (number of samples)
- [ ] Default window size: 1 (no smoothing — preserves current behaviour)
- [ ] Apply filter in `read_data()` or `parse_data()` pipeline
- [ ] Add a label/note that this is experimental (to be removed once a value is settled)
- [ ] Write unit tests for the filter using mock data — **feasible without hardware**

---

### S5 — Timed Data Recording to CSV
**Priority:** High  
**Feasibility without hardware:** ✅ Yes — I/O and timer logic, fully testable with mock

Record balance data to a CSV file for a specified duration, with a countdown before recording starts. For vestibular patient assessments.

**CSV format:** `time (s), x (kg), y (kg)` — positive/negative indicating deviation from centre.

- [ ] Add a recording duration input field (e.g. text box or spinner, default 10s)
- [ ] Add a "Start Recording" button
- [ ] Implement a 3–2–1 countdown displayed on screen before recording begins
- [ ] Record `(timestamp, x, y)` at each data frame during the recording window
- [ ] Auto-stop after the specified duration
- [ ] Save to a fixed output folder (e.g. `~/wiibble_recordings/` or `./recordings/`)
- [ ] Filename format: `recording_YYYYMMDD_HHMMSS.csv`
- [ ] Display a visual indicator (e.g. red dot / "REC") while recording is active
- [ ] Allow changing duration and starting a new recording immediately after one finishes
- [ ] Do **not** expose file path in UI for now (experimental feature)

---

## 🔧 Technical Recommendations

> Source: Code review and dev environment analysis (March 2026).

### 🔴 Critical Bugs


#### T1 — Hardcoded Windows Path for DLL
The DLL path uses Windows backslashes — breaks in the Linux devcontainer.

```python
# Current (broken on Linux)
DLL_RELATIVE_PATH = r'WiiBalanceBoardLibrary\\bin\\Debug\\net48\\WiiBalanceBoardLibrary.dll'

# Fix
DLL_RELATIVE_PATH = os.path.join('WiiBalanceBoardLibrary', 'bin', 'Debug', 'net48', 'WiiBalanceBoardLibrary.dll')
```

- [x] Replace backslash path with `os.path.join()`

---


#### T2 — Bare `except` Clauses
Silent exception swallowing hides real errors.

- [x] Replace all bare `except:` with `except Exception as e:` and log the error
- [x] At minimum add `print(f"Error: {e}")` until a logging framework is in place

---

#### T3 — Unexplained Magic Numbers
Critical constants have no documentation.

- [ ] Document `SCALE_FACTOR = 2.6441910428028423` — what does it represent? How was it derived?
- [ ] Document the hardcoded `530` threshold in `wait_for_tare()`
- [ ] Document raw data indices `3, 5, 7, 9` in `data_struct` — what HID report format are these?
- [ ] Move all constants to a dedicated `constants.py` or clearly labelled block at the top of `main.py`

---

### 🟡 Code Quality

#### T4 — Division by Zero Risk on `weight`
- [ ] Add a guard in `calculate_coordinates()` for `weight == 0`


#### T5 — Duplicate `import time`
- [x] Remove the duplicate `import time` statement (appears twice at the top of `main.py`)

#### T6 — Merge Near-Identical Functions
`show_step_on_board()` and `show_step_off_board()` are almost identical.
- [ ] Refactor into a single `show_step_instruction(screen, image, on_board: bool)` function

#### T7 — Global Mutable State
`data_struct`, `weight`, `SCREEN_WIDTH`, `SCREEN_HEIGHT`, `historical_coords` are all globals.
- [ ] Refactor into a `AppState` dataclass or class to make state explicit and testable

#### T8 — Large Commented-Out Code Blocks
Several animation logic blocks are commented out in `sensitivity_calibration()` and `wait_for_tare()`.
- [ ] Remove dead code or convert to GitHub Issues if the feature is planned

#### T9 — Inconsistent UI Approach
Some UI uses `pygame_gui`, most uses raw `pygame` calls.
- [ ] Decide on one approach and standardise — `pygame_gui` is preferred for interactive controls (especially needed for S2, S3, S4, S5)


#### T10 — Uncapped Frame Rate
`clock.tick(1000)` is effectively uncapped and will peg the CPU.
- [x] Change to `clock.tick(60)` — the board sensor rate doesn't justify anything higher

#### T11 — `resource_path()` Fragility
Falls back to `os.path.abspath(".")` which assumes the script is always run from the repo root.
- [ ] Add a check or warning if expected resource paths don't exist at startup

---

### 🟢 Developer Experience


#### T12 — Add Mock / Emulator Mode
No way to run the app without a physical Wii Balance Board.
- [x] Add a `--mock` CLI flag that feeds simulated (or scripted) sensor data
- [x] Mock should simulate realistic balance data (e.g. slow sinusoidal movement)
- [x] Enables all UI features (S1–S5) to be developed and tested without hardware
- [x] Enables CI pipeline to run basic smoke tests

#### T13 — Add Logging Framework
All feedback is via `print()`.
- [ ] Replace `print()` calls with Python's `logging` module
- [ ] Use `DEBUG` for sensor data, `INFO` for state changes, `ERROR` for failures
- [ ] Write logs to file as well as console for clinical debugging sessions

#### T14 — Add GitHub Actions CI Pipeline
No automated checks exist.
- [ ] Add workflow to lint Python (`ruff` or `flake8`)
- [ ] Add workflow to build the C# DLL (`dotnet build`)
- [ ] Add workflow to run Python unit tests (once mock mode exists — see T12)
- [ ] Add workflow to build PyInstaller executable and archive as artifact

#### T15 — Add Unit Tests
No tests exist.
- [ ] Add tests for `parse_data()` using known raw byte arrays
- [ ] Add tests for `calculate_coordinates()` with known inputs
- [ ] Add tests for the moving average filter (S4) — fully testable without hardware
- [ ] Add tests for CSV recording logic (S5) — fully testable without hardware
- [ ] Use `pytest` as the test framework

---

### 🟢 Project Structure

#### T16 — Add `pyproject.toml`
The project uses `requirements.txt` only — no modern Python project metadata.
- [ ] Create `pyproject.toml` compatible with `uv`
- [ ] Define project name, version, Python requirement (`>=3.8`), and dependencies
- [ ] Keep `requirements.txt` as a lock file or replace with `uv.lock`

#### T17 — Update README Install Instructions
README still references `pip install -r requirements.txt`.
- [ ] Update to `uv pip install -r requirements.txt` or `uv sync`
- [ ] Add a "Development Without Hardware" section covering mock mode (T12)
- [ ] Move the existing README To-Do list into this document and link to GitHub Issues

#### T18 — Convert README To-Dos to GitHub Issues
The README contains a To-Do list (battery indicator, compensation mechanism, etc.).
- [ ] Open a GitHub Issue for each item so they are trackable and assignable

---

## 💡 Notes for Development Without Hardware

The following items from this TODO can be fully developed and tested **without a Wii Balance Board**:

| Item | Why it's hardware-independent |
|------|-------------------------------|
| S1 — Cursor toggle | Pure rendering logic |
| S2 — Trail length | Operates on `historical_coords` list |
| S3 — Zoom control | Coordinate scaling multiplier |
| S4 — Moving average filter | Signal processing, testable with synthetic data |
| S5 — CSV recording | Timer + file I/O, testable with mock data |
| T2 — Exception handling | Refactoring only |
| T5 — Duplicate import | Trivial fix |
| T6 — Merge functions | Refactoring only |
| T10 — Frame rate cap | One-line change |
| T12 — Mock mode | Enables all of the above in a running app |
| T13 — Logging | Refactoring only |
| T15 — Unit tests | Use mock data |
| T16 — pyproject.toml | Project config only |
| T17 — README update | Documentation only |