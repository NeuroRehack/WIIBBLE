# TECHSPEC — WIIBBLE

> Machine- and developer-facing technical reference. Read this before modifying any module.

---

## Architecture Overview

### What it is and who it is for

WIIBBLE is a Windows desktop application used by physiotherapists in clinical rehabilitation settings. It repurposes a Nintendo Wii Balance Board as a cheap, accessible force platform — displaying live centre-of-pressure position, recording session data to CSV, and letting clinicians place rehabilitation targets on screen. Developed as part of the **EPIC-Tech study** at UQ / Griffith / Princess Alexandra Hospital.

### Technical approach and stack

- **GUI**: [DearPyGui](https://github.com/hoffstadt/DearPyGui) 2.1.1 — immediate-mode, GPU-rendered. All drawing is done via a `viewport_drawlist` (no window chrome around the canvas) to enable full-screen rendering without a title bar or borders.
- **Sensor data**: Raw 32-byte HID reports read via `hidapi` (Python). The board exposes itself as a standard HID device after Bluetooth pairing.
- **Bluetooth connection**: A C# DLL (`WiiBalanceBoardLibrary`) loaded via `pythonnet`/`clr` handles the initial Bluetooth handshake only. After `try_connection()` succeeds and disconnects, all data acquisition switches to `hid.device.read()`.
- **Language split**: Python for all application logic; C# (.NET Framework 4.8) for the Bluetooth trigger only.
- **Build**: Nuitka standalone executable via `compiler.bat`. Dependency management via `uv` + `pyproject.toml`.
- **CI**: GitHub Actions (`windows-latest`): `ruff` lint/format gate → `pytest` with ≥80% coverage gate.

### Top-level organisation

All Python source files live flat in the repo root. There is no `src/` layout — `pythonpath = ["."]` in pytest config reflects this. The C# project lives in `WiiBalanceBoardLibrary/`. Assets (fonts, images) are in `assets/` and `images/`. Recorded CSVs go to `recordings/`. Settings persist to `~/.wiibble/settings.json`.

---

## Module Responsibilities

| Module | Owns | Does NOT own |
|---|---|---|
| `main.py` | DPG context lifecycle, `argparse`, logging setup, screen-size detection, `AppState`/`Settings` construction | No application logic; importing it in tests is safe because all dpg/app code is under `if __name__ == "__main__"` |
| `app.py` | Session lifecycle (connect → tare → calibrate → main loop → restart), render orchestration, recording state machine, session action dispatch | Drawing (delegated to `ui.py`), input handling (delegated to `input.py`), sensor maths (delegated to `data_processing.py`) |
| `ui.py` | All DPG draw calls — canvas, cursor, trail, targets, calibration screens, stats bar, toolbar widgets | Sensor computation, state mutation (receives values as arguments, does not read `AppState` directly except `draw_main_screen`) |
| `input.py` | Mouse click, drag, release, and wheel callbacks; target creation/resize; pan; zoom-on-scroll | Does not read sensor data; writes `session_state["action"]` for `app.py` to process |
| `data_processing.py` | Pure sensor pipeline: `read_data`, `parse_data`, `tare`, `apply_filter`, `calculate_coordinates`, `calculate_force_deviation_kg`, `measure_weight` | No DPG imports; no state; fully unit-testable without hardware |
| `calibration.py` | Tare and sensitivity calibration workflows (blocking loops that render calibration screens inline) | Does not own the DPG render loop — calls `dpg.render_dearpygui_frame()` directly inside its loops |
| `state.py` | `AppState` (mutable runtime state) and `Settings` (persisted user preferences, loaded/saved as JSON) | No DPG imports; no sensor logic |
| `constants.py` | Every magic number in the app: hardware IDs, HID byte indices, scale factors, thresholds, UI layout sizes, zoom range | No logic; import-only |
| `theme.py` | DPG colour palette, global theme application, font loading, `bind_text_font()`, `get_stats_bar_color()` | No drawing of application content; only applies styling hooks |
| `recording.py` | `_save_recording_csv()` — serialises a buffer of `(elapsed, x_kg, y_kg)` tuples to a timestamped CSV in `recordings/` | Does not decide when to record; called by `app.py` |
| `mock_board.py` | `MockHIDDevice` — drop-in `hid.device()` replacement that generates physics-plausible sensor data for the configured scenario | Used only when `--mock` is passed; never imported by non-mock paths |
| `board_connection.py` | C# DLL loading via `pythonnet`, Bluetooth connection trigger (`try_connection()`), immediate disconnect | Not used for ongoing data acquisition — that goes through `hid.device` directly |
| `resources.py` | Path resolution for bundled assets, working in both dev mode (relative CWD) and Nuitka standalone (exe directory) | Does not load the assets themselves; returns resolved path strings |

---

## Key Data Flows

### 1. Live sensor → cursor position (every frame)

1. `app.py / _process_frame_data()` calls `data_processing.read_data(device)` → raw 32-byte list from HID
2. `parse_data(data, app_state.data_struct)` — extracts 4 corner floats, applies tare, multiplies by `SCALE_FACTOR` → `corners` dict (kg per corner)
3. `apply_filter(corners, app_state.filter_buffer, settings.filter_window)` — moving-average smooth in-place; `filter_window=1` is a pass-through
4. `calculate_coordinates(tl, tr, bl, br, weight, screen_w, screen_h)` — normalises by body weight, scales to pixels from screen centre → `(raw_x, raw_y)`
5. `raw_x * settings.zoom_factor + pan_offset_x` → `app_state.ball_x` (screen pixel)
6. `ui.draw_main_screen(dl, ..., ball_x, ball_y, ...)` renders cursor, trail, and targets to the `viewport_drawlist`

### 2. Session startup (connect → tare → calibrate)

1. `board_connection.try_connection(dll_path)` loads the C# DLL via `clr`, calls `BalanceBoardManager.Connect()`, then immediately disconnects — this triggers the OS Bluetooth handshake
2. `hid.device().open(VENDOR_ID, PRODUCT_ID)` opens the board as a raw HID device for ongoing data
3. `calibration.wait_for_tare(device, dl, app_state)` — renders "Step OFF" screen, loops until 20 stable readings below `TARE_MAX_WEIGHT`
4. `data_processing.tare(device, app_state.data_struct)` — averages 10 readings, writes baseline into `data_struct[corner]["tare"]`
5. `calibration.sensitivity_calibration(device, dl, app_state)` — renders "Step ON" screen, loops until 20 stable readings > baseline + `CALIB_MIN_WEIGHT_DELTA`; returns body weight → `app_state.weight`

### 3. Recording: countdown → buffer → CSV

1. Toolbar "Start Recording" button sets `app_state.is_countdown = True`, `app_state.countdown_value = 3`
2. `app.py / _update_countdown_and_recording()` ticks countdown each second; at zero sets `app_state.is_recording = True`, captures `record_start_time`
3. Each frame: `calculate_force_deviation_kg(tl, tr, bl, br)` → `(x_kg, y_kg)` appended with elapsed time to `app_state.record_buffer`
4. When `elapsed >= app_state.record_duration` (or manual stop): `recording._save_recording_csv(record_buffer)` → `recordings/recording_YYYYMMDD_HHMMSS.csv` with columns `time (s), x (kg), y (kg)`

Note: CSVs record **force deviation in kg**, not screen pixels — the recorded values are sensor-space, independent of zoom/pan/sensitivity settings.

---

## Dependencies

| Package | Version | Why this project uses it |
|---|---|---|
| `dearpygui` | `==2.1.1` | Immediate-mode, GPU-rendered GUI. Redraws the full canvas every frame without layout passes, which is the natural model for real-time sensor visualisation. `viewport_drawlist` enables true full-screen drawing without window chrome. Must be pinned — DPG breaks API between minor versions. |
| `hidapi` | `==0.14.0.post2` | The only Python library that reads raw HID reports without requiring a kernel driver. The Wii Balance Board exposes sensor data as 32-byte HID reports after Bluetooth pairing. |
| `pythonnet` | `==3.0.3` | Required to load the C# `WiiBalanceBoardLibrary.dll` at runtime via `clr.AddReference()`. The underlying Wii Bluetooth pairing/connection logic was already implemented in C# (from WiiBalanceWalker); `pythonnet` bridges it without a rewrite. Must be 3.x — the 2.x API is incompatible. |
| `numpy` | `==1.24.4` | Used only in `tare()` to average 10 HID readings as array operations. Pinned to the last version supporting Python 3.8; upgrade with care if minimum Python version changes. |
| `pytz` | latest | Timezone-aware timestamps in recording filenames. |
| `nuitka` | `>=2.0` (dev) | Compiles to a standalone `.exe` for deployment on clinical machines without Python installed. Chosen over PyInstaller because it produces a true compiled binary (less AV false-positives, smaller startup time). |
| `pytest` / `pytest-cov` | `>=7.0` / `>=5.0` (dev) | Standard test runner; coverage gate at ≥80% enforced in `pyproject.toml`. DPG and board-dependent modules are excluded from coverage (see `[tool.coverage.run] omit`). |
| `ruff` | `>=0.4` (dev) | Lint and format gate in CI. Config in `pyproject.toml` — `E501` (line length) is ignored; line length is 100. |

**C# dependencies** (built by `dotnet build` in `WiiBalanceBoardLibrary/`):
- `.NET Framework 4.8` — required for the WiiBalanceBoardLibrary DLL (targets `net48`)
- `.NET 8.0` SDK — used to run `dotnet build`

---

## Conventions & Patterns

### Naming

- `UPPER_SNAKE_CASE` for all constants in `constants.py`
- `_leading_underscore` for module-private functions throughout (e.g. `_run_session`, `_save_recording_csv`)
- `data_struct` — always a dict of dicts: `{corner_name: {"rawIndex": int, "tare": float}}`
- `corners` — always a dict: `{"top_right": float, "top_right": float, "top_left": float, "bottom_left": float}`
- `dl` — always the DPG `viewport_drawlist` tag/item, passed explicitly through call chains
- `session_state` — always a plain `dict` with keys `"action"`, `"toolbar_visible"`, `"toolbar_enabled"`

### Architectural patterns

- **Pure pipeline**: `data_processing.py` functions take inputs, return outputs, have no side effects, and import no DPG or state. This is what makes them unit-testable.
- **Action bus**: Input handlers (`input.py`) write `session_state["action"] = "some_action"` rather than calling `app.py` functions directly. `_handle_session_action()` in `app.py` processes and clears the action each frame. This decouples input callbacks from session logic.
- **Flat import of DPG**: Every module that needs DPG imports it directly (`import dearpygui.dearpygui as dpg`). There is no DPG wrapper layer.
- **Settings labelled S1–S6**: Comments in `state.py` and `app.py` label each setting field (e.g. `# S1: cursor_mode`) to cross-reference with the original specification.
- **`session_state` not `AppState`**: Transient UI state that doesn't survive a restart (toolbar visibility, current action) lives in the `session_state` dict, not in `AppState`. `AppState.reset()` does not touch `session_state`.
- **Tests mock DPG at the boundary**: Tests that exercise `input.py` use `monkeypatch` on `dpg` calls. Hardware-dependent modules (`board_connection`, `calibration`, `ui`, `app`) are excluded from the coverage target.

### Contributor rules

- Never call `dpg.*` from `data_processing.py`, `state.py`, `recording.py`, or `constants.py`.
- Never put magic numbers directly in `app.py` or `ui.py` — add them to `constants.py`.
- All asset paths must go through `resources.resource_path()` — never use `open("images/...")` raw.
- Adding a new `Settings` field: add it to the `@dataclass` with a default; `Settings.load()` will handle old saved files automatically (unknown keys are silently dropped).
- Do not call `dpg.render_dearpygui_frame()` outside of `app.py` and `calibration.py` — calibration owns its own blocking render loops.

---

## Non-Obvious Design Decisions

### Two separate board connection mechanisms

`board_connection.py` and `hid.device()` serve different purposes. The C# DLL is called once at startup via `try_connection()` only to trigger the Bluetooth OS handshake — it connects and immediately disconnects. All subsequent data acquisition uses `hidapi` (`hid.device().open(VENDOR_ID, PRODUCT_ID)`). This split exists because the Wii Balance Board requires a Bluetooth-level connection trigger that the C# library handles, but `hidapi` is faster and simpler for the continuous 32-byte HID polling. A contributor who sees `board_connection.py` not being called during `read_data()` is not looking at a bug.

### `SCALE_FACTOR` is empirically derived, not from the spec

`SCALE_FACTOR = 2.6441910428028423` was determined by regression against known weights, not from any Nintendo datasheet. It is the single most important constant for measurement accuracy. It can vary between individual boards and should be updated via a future calibration feature (see TODO). Do not round it.

### Raw byte encoding uses `data[i] + data[i+1] / 255`

The HID report encodes each sensor value as a two-byte pair: integer part at index `i`, fractional part at `i+1`. The denominator is **255**, not 256. This matches the WiiBalanceBoardLibrary HID report format and is validated by tests in `test_data_processing.py`. Using 256 instead would cause a systematic ~0.3% error.

### Filter applied before coordinate scaling, not after

`apply_filter()` is called on raw corner kg values before `calculate_coordinates()`. If filtering were applied after, small absolute noise in kg would be amplified by `COORD_SCALE * screen_width` (≈ 1100+ pixels per kg on a 1920px screen). At the sensor level, 0.1 kg noise is tolerable; at screen-coordinate level it becomes 10+ pixels of jitter.

### Zoom is exponential, stored as a slider exponent

`settings.zoom_factor = ZOOM_SCALE ** slider_value` where `ZOOM_SCALE = 1.01`. The slider widget holds the exponent (an integer from −200 to 600); the actual multiplier is `1.01^x`. This gives perceptually uniform zoom steps. Converting back from `zoom_factor` to slider position requires `log(zoom_factor) / log(ZOOM_SCALE)`, which appears in both `_on_zoom_to_bbox` and the mouse-wheel handler — both must stay in sync.

### `session_state["action"]` is a command, cleared immediately after dispatch

`_handle_session_action()` clears the action after processing. If a handler forgets to call `_clear_session_action()`, the action will be re-dispatched every frame until the next frame overwrites it. The `"restart"` action is the exception — it returns early from the session loop before clearing, because the session is being torn down anyway.

### `AppState.reset()` intentionally preserves `weight`, `screen_width`, `screen_height`

These three reflect hardware calibration and viewport dimensions — not session content. Resetting them would require re-calibrating after every "RESTART", which is the wrong UX. All other fields are reset. A new developer may see this as incomplete and "fix" it accidentally.

### `MockHIDDevice` uses a time-based phase model, not read-count based

`tare()` and `measure_weight()` each call `device.read()` **10 times in a tight loop**. A read-count based phase transition would exhaust "tare" phase in a single `measure_weight()` call. The phase model uses `time.time()` with an explicit 20ms sleep per read in calibration phases to pace the mock at ~0.5s per measurement sample — matching realistic board behaviour.

### Stats bar redraws only on value change

`_stats_cache` in `ui.py` stores the last drawn values. `update_stats_bar()` is a no-op if the new values match the cache. This prevents sub-pixel floating point jitter (e.g. `12.3499` vs `12.3501`) from causing a redraw every frame, which was causing blurry text due to fractional pixel positions.

### `draw_text` fonts loaded at 100px

DearPyGui's default font is ~13px. Calling `draw_text(size=40)` upscales the 13px bitmap — result is blurry. The fix is to load Roboto-Regular at 100px in the DPG font registry and call `bind_text_font(item_tag)` on every `draw_text` item. ImGui then downscales from 100px to any requested size ≤ 100px, which is always sharp. The `_crisp_text()` helper in `ui.py` enforces this pattern.

### DPG init order is strict and non-negotiable

```
create_context() → load_fonts() → setup_dearpygui() → create_viewport() → show_viewport()
```
`load_fonts()` must come before `setup_dearpygui()` — the font registry must exist before DPG initialises its render pipeline. Swapping these produces a crash with no useful error message.

### `ctypes` for screen size detection

`ctypes.windll.user32.GetSystemMetrics()` is used instead of a tkinter or win32api call. Tkinter creates a hidden window and a Windows message loop that interferes with DPG's own message loop. `ctypes.GetSystemMetrics` is a pure Win32 API call with no side effects.

### Recording stores kg, not pixels

`record_buffer` stores `(elapsed_s, x_kg, y_kg)` — the force deviation in kg, not screen coordinates. This makes recordings independent of zoom, pan, sensitivity, and screen resolution, and directly meaningful as clinical measurements. The CSV can be analysed without knowing any display parameters.

### `Settings.load()` ignores unknown keys

When loading `settings.json`, keys that don't match current `Settings` fields are silently dropped. This means an older settings file (from a version with more fields) won't crash the app after a field is removed. New fields added to `Settings` with defaults will read as their default on first load from an old file.

---

## File Index

`main.py` — DPG context setup, argparse, logging configuration, and screen-size detection; calls `app.run()`.

`app.py` — Full session lifecycle: connection loop, tare/calibration startup, main render loop, recording state machine, toolbar action dispatch, and zoom/pan logic.

`ui.py` — All DPG draw calls: canvas, crosshairs, cursor (avatar and circle), trail, target circles, calibration instructions, stats bar, and toolbar widget construction.

`input.py` — Mouse click, drag, release, and wheel handlers; target creation/resize interaction; Ctrl+drag pan; Ctrl+scroll zoom-around-cursor.

`data_processing.py` — Pure sensor pipeline: HID read, byte parsing with tare, moving-average filter, coordinate calculation, weight measurement, and force deviation.

`calibration.py` — Blocking calibration workflows: `wait_for_tare()` (board empty detection) and `sensitivity_calibration()` (body weight detection), each with inline screen rendering.

`state.py` — `AppState` dataclass (mutable runtime state, reset on restart) and `Settings` dataclass (persisted user preferences, loaded/saved as `~/.wiibble/settings.json`).

`constants.py` — All magic numbers: hardware USB IDs, HID byte indices, `SCALE_FACTOR`, calibration thresholds, zoom range, UI layout sizes, and the DLL path.

`theme.py` — Colour palette, global DPG theme application, FontAwesome icon loading, Roboto 100px crisp-text font loading, and `bind_text_font()` / `get_stats_bar_color()` helpers.

`recording.py` — `_save_recording_csv(record_buffer)`: serialises a list of `(elapsed, x_kg, y_kg)` to a timestamped CSV file under `recordings/`.

`mock_board.py` — `MockHIDDevice`: drop-in `hid.device()` replacement generating physics-plausible sensor data in six named scenarios; phase model mirrors real tare → step-on → normal flow.

`board_connection.py` — C# DLL loader via `pythonnet`; `try_connection()` triggers the Bluetooth OS handshake and immediately disconnects; not used for data acquisition.

`resources.py` — `resource_path()`: resolves asset paths relative to CWD in dev mode and relative to the exe directory in Nuitka standalone builds; pre-resolves commonly needed paths at import time.

`WiiBalanceBoardLibrary/BalanceBoardManager.cs` — C# class that wraps WiimoteLib to connect/disconnect a Wii Balance Board via Bluetooth and expose sensor data as .NET events.

`WiiBalanceBoardLibrary/WiiBalanceBoardLibrary.csproj` — C# project file targeting `.NET Framework 4.8`; outputs `WiiBalanceBoardLibrary.dll` to `bin/Debug/net48/`.

`tests/conftest.py` — Shared pytest fixtures: `data_struct`, `zero_data`, `balanced_corners`.

`tests/test_data_processing.py` — Unit tests for `parse_data`, `apply_filter`, `calculate_force_deviation_kg`, `calculate_coordinates`.

`tests/test_state.py` — Unit tests for `Settings` defaults, save/load round-trip, graceful fallback, and `AppState.reset()`.

`tests/test_recording.py` — Unit tests for `_save_recording_csv`: filename format, CSV headers, row precision, empty buffer.

`tests/test_input.py` — Unit tests for `_handle_canvas_click`, `_handle_target_drag`, `_handle_target_release`, `_handle_pan_drag`, `_handle_pan_release`, `_handle_mouse_wheel`, and `register_input_handlers`.

`pyproject.toml` — Project metadata, pinned runtime dependencies, dev extras (`nuitka`, `pytest`, `ruff`), pytest config (testpaths, coverage gate ≥80%, DPG/hardware modules excluded), and ruff config.

`compiler.bat` — Nuitka build script producing `outputBuild/WIIBBLE/WIIBBLE.exe`; copies DLL and assets alongside the executable.

`.github/workflows/ci.yml` — GitHub Actions: `ruff check` + `ruff format --check` (lint job), then `pytest -v` with coverage (test job); runs on push to `develop`/`main` and PRs to `main`.
