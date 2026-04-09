# WIIBBLE — Testing Implementation Plan

> **Temporary working document.** Delete after implementation is complete.
>
> **Hardware note:** No physical board available. All verification uses `--mock` mode only.

---

## Table of Contents

1. [Overview](#overview)
2. [Current State](#current-state)
3. [Tools & Configuration](#tools--configuration)
4. [Test File Structure](#test-file-structure)
5. [Implementation Stages](#implementation-stages)
   - [Stage 0 — Baseline Verification (no changes yet)](#stage-0--baseline-verification-no-changes-yet)
   - [Stage 1 — Lint Gate (ruff)](#stage-1--lint-gate-ruff)
   - [Stage 2 — Test Infrastructure (conftest)](#stage-2--test-infrastructure-conftest)
   - [Stage 3 — data_processing.py Tests](#stage-3--data_processingpy-tests)
   - [Stage 4 — state.py Tests](#stage-4--statepy-tests)
   - [Stage 5 — Extract _save_recording_csv → recording.py](#stage-5--extract-_save_recording_csv--recordingpy)
   - [Stage 6 — recording.py Tests](#stage-6--recordingpy-tests)
   - [Stage 7 — Coverage Gate](#stage-7--coverage-gate)
   - [Stage 8 — GitHub Actions CI](#stage-8--github-actions-ci)
6. [Full Verification Commands Reference](#full-verification-commands-reference)
7. [Coverage Targets](#coverage-targets)
8. [What Is Explicitly Out of Scope](#what-is-explicitly-out-of-scope)

---

## Overview

WIIBBLE already has `pytest>=7.0` and `ruff>=0.4` declared in `pyproject.toml` dev extras, but the `tests/` folder is empty. This plan adds:

- **Syntax/lint gate** via `ruff check` + `ruff format --check`
- **Unit tests** for all pure-function pipeline logic
- **Persistence tests** for `Settings` load/save
- **CSV recording tests** for the recording output function
- **GitHub Actions CI** to enforce all of the above on every push

At each stage: implement → run the test suite → launch the app in mock mode to confirm nothing is broken.

---

## Current State

| Item | Status |
|------|--------|
| `tests/` folder | Empty |
| `scripts/` folder | Empty |
| `pytest` installed | Declared in dev extras — run `uv sync --extra dev` |
| `ruff` installed | Declared in dev extras |
| Existing tests | None |
| CI pipeline | None |
| Pure testable functions | 4 (in `data_processing.py`) |
| Settings persistence | `state.Settings.load()` / `.save()` |
| Recording logic | `_save_recording_csv()` in `app.py` (needs extraction) |

---

## Tools & Configuration

| Tool | Purpose | Config location |
|------|---------|----------------|
| `pytest` | Unit test runner | `pyproject.toml` → `[tool.pytest.ini_options]` |
| `pytest-cov` | Coverage reporting | Add to `pyproject.toml` dev extras |
| `ruff check` | Lint (pyflakes + pycodestyle + isort) | `pyproject.toml` → `[tool.ruff]` |
| `ruff format --check` | Format compliance | Same config |

**Install dev extras (run once):**
```powershell
uv sync --extra dev
```

**Add `pytest-cov` to `pyproject.toml`** (during Stage 7):
```toml
[project.optional-dependencies]
dev = [
    "nuitka>=2.0",
    "pytest>=7.0",
    "pytest-cov>=5.0",
    "ruff>=0.4",
]
```

---

## Test File Structure

```
tests/
  conftest.py                  # Shared fixtures (data_struct, corners, tmp settings dir)
  test_data_processing.py      # parse_data, apply_filter, calculate_force_deviation_kg,
                               # calculate_coordinates
  test_state.py                # Settings defaults, save/load round-trip, graceful fallback
  test_recording.py            # _save_recording_csv: header, rows, format, filename pattern
recording.py                   # NEW — extracted from app.py (Stage 5)
```

---

## Implementation Stages

---

### Stage 0 — Baseline Verification (no changes yet)

> **Goal:** Confirm the app works in mock mode before touching anything. This is the reference state.

**Commands:**
```powershell
# 1. Install dev extras (pytest, ruff)
uv sync --extra dev

# 2. Confirm ruff is available
uv run ruff --version

# 3. Confirm pytest is available
uv run pytest --version

# 4. Confirm the app launches and runs in mock mode (let it run for ~10 seconds, then Ctrl+C)
uv run python main.py --mock --mock-scenario sway
```

**Pass criteria:**
- `ruff --version` and `pytest --version` print version numbers without error
- App window opens, calibration screens appear, cursor moves on screen
- No Python exceptions in the terminal output

---

### Stage 1 — Lint Gate (ruff)

> **Goal:** Establish ruff as the syntax and style gate. Identify and fix any pre-existing violations before writing tests.

**What changes:**
- Run `ruff check .` to see current violations
- Fix any real violations in existing source files (not just ignoring them)
- Verify `ruff format --check .` passes

**Commands:**
```powershell
# Check for lint violations
uv run ruff check .

# Check for formatting violations (read-only, does not modify files)
uv run ruff format --check .

# If you want ruff to auto-fix safe lint issues:
uv run ruff check . --fix

# If you want ruff to auto-format files:
uv run ruff format .
```

**After Stage 1 — verify app still runs:**
```powershell
uv run python main.py --mock --mock-scenario sway
```

**Pass criteria:**
- `ruff check .` exits with code 0 (zero violations)
- `ruff format --check .` exits with code 0
- App still launches and runs in mock mode

---

### Stage 2 — Test Infrastructure (conftest)

> **Goal:** Create `tests/conftest.py` with shared fixtures that every test file will use. No test logic yet — just scaffolding.

**What changes:**
- Create `tests/conftest.py`

**Contents of `tests/conftest.py`:**

```python
import pytest

# ── Sensor data_struct fixture ───────────────────────────────────────────────
@pytest.fixture
def data_struct():
    """Default data_struct matching AppState, with tare=0."""
    return {
        "top_right":    {"rawIndex": 3, "tare": 0},
        "bottom_right": {"rawIndex": 5, "tare": 0},
        "top_left":     {"rawIndex": 7, "tare": 0},
        "bottom_left":  {"rawIndex": 9, "tare": 0},
    }

@pytest.fixture
def zero_data():
    """A zeroed 32-byte HID report."""
    return [0] * 32

@pytest.fixture
def balanced_corners():
    """All four corners equal — represents a perfectly balanced stance."""
    return {"top_right": 9.0, "bottom_right": 9.0, "top_left": 9.0, "bottom_left": 9.0}
```

**Commands after Stage 2:**
```powershell
# Run pytest — should collect 0 tests but exit cleanly (no errors)
uv run pytest -v

# App still runs
uv run python main.py --mock --mock-scenario sway
```

**Pass criteria:**
- `pytest -v` exits with 0 (no items / no failures)
- App still launches

---

### Stage 3 — data_processing.py Tests

> **Goal:** Full unit test coverage for the four pure pipeline functions. No hardware, no UI, no DearPyGui import.

**What changes:**
- Create `tests/test_data_processing.py`

**Test cases to implement:**

#### `parse_data()`
| Test | Input | Expected |
|------|-------|----------|
| All-zero bytes, tare=0 | `[0]*32` | All corners = `0.0` |
| Single corner, known bytes, tare=0 | `data[3]=100, data[4]=128` | `top_right = round((100 + 128/255) * SCALE_FACTOR, 2)` |
| All four corners simultaneously | Distinct values at indices 3,4,5,6,7,8,9,10 | Each corner independently correct |
| Tare offset applied | `data[3]=100, data[4]=0, tare=50` | `top_right = round((100 - 50) * SCALE_FACTOR, 2)` |
| Max byte values | `data[i]=255, data[i+1]=255` | `round((255 + 255/255) * SCALE_FACTOR, 2)` |

#### `apply_filter()`
| Test | Setup | Expected |
|------|-------|----------|
| `filter_window=1`, single frame | Any corners | Output equals input; buffer length = 1 |
| `filter_window=1`, second frame | Same corners again | Output equals input; buffer length stays 1 (oldest dropped) |
| `filter_window=2`, two identical frames | corners = 9.0 each | Output equals 9.0 (average of two identical frames) |
| `filter_window=2`, two different frames | Frame1=10.0, Frame2=20.0 | Output = 15.0 per corner |
| `filter_window=5`, only 3 frames so far | Frames of 10, 20, 30 | Output = 20.0 (partial average, no padding) |
| Buffer does not exceed window size | Call 10 times with `window=3` | `len(filter_buffer) == 3` after all calls |

#### `calculate_force_deviation_kg()`
| Test | Input `(tl, tr, bl, br)` | Expected `(x, y)` |
|------|--------------------------|-------------------|
| Perfectly balanced | `(9, 9, 9, 9)` | `(0, 0)` |
| All weight on right | `(0, 20, 0, 20)` | `(40, 0)` |
| All weight on left | `(20, 0, 20, 0)` | `(-40, 0)` |
| All weight forward (top) | `(20, 20, 0, 0)` | `(0, 40)` |
| All weight back (bottom) | `(0, 0, 20, 20)` | `(0, -40)` |
| Asymmetric diagonal | `(10, 5, 3, 2)` | `x=(5+2)-(10+3)=-6`, `y=(10+5)-(3+2)=10` → `(-6, 10)` |

#### `calculate_coordinates()`
| Test | Input | Expected |
|------|-------|----------|
| `weight=0` guard | Any corners, `weight=0` | `(0.0, 0.0)` — no ZeroDivisionError |
| Balanced stance | Equal corners, any non-zero weight | `(0.0, 0.0)` |
| `zoom=2.0` doubles output | Any unbalanced corners | `output_zoom2 == 2 * output_zoom1` |
| Double `screen_width` doubles `x` | Same corners, 2x width | `x_doubled == 2 * x_original` |
| Left lean yields positive `x` | More weight on left side | Check sign of `x` matches expected convention |
| Forward lean yields positive `y` | More weight on top side | Check sign of `y` |

**Commands after Stage 3:**
```powershell
# Run tests — all should pass
uv run pytest tests/test_data_processing.py -v

# Run full suite
uv run pytest -v

# Lint check still passes
uv run ruff check .

# App still runs in mock mode
uv run python main.py --mock --mock-scenario sway
uv run python main.py --mock --mock-scenario lean_left
uv run python main.py --mock --mock-scenario still
```

**Pass criteria:**
- All `test_data_processing.py` tests pass
- `ruff check .` passes
- App launches and cursor moves correctly in all three mock scenarios

---

### Stage 4 — state.py Tests

> **Goal:** Test `Settings` persistence: defaults, save/load round-trip, graceful fallback for missing or corrupt file.

**Important:** `SETTINGS_PATH` in `state.py` is a relative path (`.wiibble/settings.json`). Tests must redirect it to a temp directory via `monkeypatch.chdir(tmp_path)` so tests don't write to the real project directory.

**What changes:**
- Create `tests/test_state.py`

**Test cases to implement:**

| Test | Description |
|------|-------------|
| Default values | `Settings()` has `trail_length=100`, `zoom_factor=1.0`, `filter_window=1`, `record_duration=10`, `cursor_mode="avatar"`, `sensitivity=1.0` |
| `load()` with no file | Returns defaults, no exception |
| `save()` then `load()` round-trip | All fields survive JSON round-trip with correct types |
| `load()` with partial JSON | Missing fields are filled with defaults; present fields are used |
| `load()` with corrupt JSON | Returns defaults, no exception |
| `load()` with unknown keys in JSON | Unknown keys silently ignored; valid defaults applied |
| `toggle_cursor_mode()` | Switches `avatar` → `circle` → `avatar` |
| `AppState.reset()` | After reset, `ball_x=0`, `ball_y=0`, `is_recording=False`, `record_buffer=[]`, `filter_buffer=[]` |

**Commands after Stage 4:**
```powershell
uv run pytest tests/test_state.py -v
uv run pytest -v
uv run ruff check .
uv run python main.py --mock --mock-scenario sway
```

**Pass criteria:** Same as Stage 3 — all tests pass, no ruff violations, app still runs.

---

### Stage 5 — Extract `_save_recording_csv` → `recording.py`

> **Goal:** Move `_save_recording_csv()` out of `app.py` into a new `recording.py` module so it can be tested without importing DearPyGui (which would crash in a headless test environment).

**Why this is needed:** `app.py` imports `dearpygui` at the top level. Importing it in a test environment without a display will fail. Extracting the function avoids this entirely.

**What changes:**
1. Create `recording.py` with `_save_recording_csv()` moved into it (same logic, no changes to the function body)
2. In `app.py`: replace `def _save_recording_csv(...)` with `from recording import _save_recording_csv`
3. No other logic in `app.py` changes — the two call sites (`line 707`, `line 713`) remain identical

**Commands after Stage 5:**
```powershell
# Verify app STILL runs after the refactor — this is the critical check for this stage
uv run python main.py --mock --mock-scenario sway

# Also test the step_on_off scenario to exercise the recording path
uv run python main.py --mock --mock-scenario step_on_off

# Lint check
uv run ruff check .

# Full test suite (no new tests yet, but existing ones must still pass)
uv run pytest -v
```

**Pass criteria:**
- App launches and behaves identically in mock mode — recording still works
- No import errors
- Existing tests still pass
- `ruff check .` passes

> **Risk:** Low. This is a pure mechanical extraction — function body is unchanged, call sites are unchanged. The only change is the module boundary.

---

### Stage 6 — recording.py Tests

> **Goal:** Test `_save_recording_csv()` for correct file creation, header, row formatting, and filename pattern.

**What changes:**
- Create `tests/test_recording.py`
- Add a `recordings_dir` fixture to `conftest.py` using `monkeypatch.chdir(tmp_path)` so files go to a temp directory

**Test cases to implement:**

| Test | Description |
|------|-------------|
| Empty buffer | Creates file with header row only; no data rows |
| Header format | First row is exactly `["time (s)", "x (kg)", "y (kg)"]` |
| Single data row | Values formatted to 3 decimal places (`"0.010"`, not `"0.01"`) |
| Three data rows | All rows present, correct values |
| Filename pattern | Filename matches `recording_\d{8}_\d{6}\.csv` |
| Directory created | `recordings/` directory is created if it doesn't exist |
| Negative values | Negative `x`/`y` values are written with leading minus sign |

**Commands after Stage 6:**
```powershell
uv run pytest tests/test_recording.py -v
uv run pytest -v
uv run ruff check .
uv run python main.py --mock --mock-scenario sway
```

**Pass criteria:** All tests pass, ruff passes, app still runs.

---

### Stage 7 — Coverage Gate

> **Goal:** Add `pytest-cov` and confirm coverage targets are met. Add coverage thresholds to `pyproject.toml`.

**What changes:**
1. Add `pytest-cov>=5.0` to `pyproject.toml` dev extras
2. Add coverage config to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--cov=data_processing --cov=state --cov=recording --cov-report=term-missing --cov-fail-under=80"
```

**Commands after Stage 7:**
```powershell
# Re-sync to pick up pytest-cov
uv sync --extra dev

# Run with coverage (now automatic via addopts)
uv run pytest -v

# Or run manually for a detailed report
uv run pytest --cov=data_processing --cov=state --cov=recording --cov-report=term-missing -v

# Full check: lint + tests
uv run ruff check .
uv run ruff format --check .
uv run pytest -v

# App still runs
uv run python main.py --mock --mock-scenario sway
```

**Pass criteria:**
- `data_processing.py`: ≥90% line coverage
- `state.py`: ≥80% line coverage
- `recording.py`: 100% line coverage
- `pytest` exits with code 0 (coverage threshold met)

---

### Stage 8 — GitHub Actions CI

> **Goal:** Enforce the lint gate and test suite on every push to `develop`/`main` and every PR to `main`.

**What changes:**
- Create `.github/workflows/ci.yml`

**CI file structure:**

```yaml
name: CI

on:
  push:
    branches: [develop, main]
  pull_request:
    branches: [main]

jobs:
  lint:
    name: Lint (ruff)
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync --extra dev
      - run: uv run ruff check .
      - run: uv run ruff format --check .

  test:
    name: Unit Tests (pytest)
    runs-on: windows-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync --extra dev
      - run: uv run pytest -v
      - name: Upload coverage report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: coverage-report
          path: .coverage
```

> **Note:** The `dotnet build` CI job (for the C# DLL) is a separate workflow and not part of this plan.

**Commands after Stage 8:**
```powershell
# Final local verification pass — run all checks in sequence
uv run ruff check .
uv run ruff format --check .
uv run pytest -v
uv run python main.py --mock --mock-scenario sway
uv run python main.py --mock --mock-scenario lean_right
uv run python main.py --mock --mock-scenario still
```

**Pass criteria:**
- All local checks pass
- Push to `develop` → GitHub Actions runs and both jobs turn green

---

## Full Verification Commands Reference

Run this sequence after **any** stage to confirm nothing is broken:

```powershell
# 1. Lint check
uv run ruff check .

# 2. Format check
uv run ruff format --check .

# 3. Tests with coverage
uv run pytest -v

# 4. App smoke test — mock sway (main scenario)
uv run python main.py --mock --mock-scenario sway

# 5. App smoke test — mock still (verifies no movement is fine too)
uv run python main.py --mock --mock-scenario still

# 6. App smoke test — mock lean (verifies directional bias)
uv run python main.py --mock --mock-scenario lean_left
```

> **Expected app behavior in mock mode:**
> - App window opens
> - "Connecting..." screen appears briefly, then calibration screens appear
> - Cursor moves on the main session screen (scenario-dependent)
> - No Python tracebacks in the terminal

---

## Coverage Targets

| Module | Target | Notes |
|--------|--------|-------|
| `data_processing.py` | ≥90% | 4 pure functions; the only uncoverable lines are hardware I/O (`read_data`, `tare`, `measure_weight`) |
| `state.py` | ≥80% | `Settings.save/load` fully covered; `AppState` drawing logic not covered |
| `recording.py` | 100% | Small module, fully testable |
| `app.py` | Not targeted | DearPyGui + hardware coupling; exclude from coverage gate |
| `ui.py`, `theme.py`, `calibration.py` | Not targeted | Require DearPyGui display context |

---

## What Is Explicitly Out of Scope

| Item | Reason |
|------|--------|
| `ui.py` / `theme.py` tests | Require live DearPyGui context (display) — not feasible headless |
| `calibration.py` tests | Tightly coupled to hardware + DearPyGui rendering loop |
| `read_data()` / `tare()` / `measure_weight()` unit tests | Require hardware device; mock integration tests are a better fit (future work) |
| Integration tests using `MockHIDDevice` | Good future follow-on — `MockHIDDevice` supports this, but scope is limited here |
| `dotnet build` CI job | Separate workflow; not part of this plan |
| UI/visual regression testing | No feasible tooling for DearPyGui |

---

## Stage Checklist

| Stage | Description | Status |
|-------|-------------|--------|
| 0 | Baseline verification — app runs in mock mode | ✅ |
| 1 | Lint gate — ruff check + format check passes | ✅ |
| 2 | Test infrastructure — conftest.py created | ✅ |
| 3 | data_processing.py tests — all 4 pure functions covered | ✅ |
| 4 | state.py tests — Settings save/load/defaults covered | ✅ |
| 5 | Extract _save_recording_csv → recording.py | ✅ |
| 6 | recording.py tests — CSV output fully covered | ✅ |
| 7 | Coverage gate — pytest-cov thresholds enforced | ✅ |
| 8 | GitHub Actions CI — lint + test jobs on push | ✅ |
