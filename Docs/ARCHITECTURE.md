# WIIBBLE — Architecture Overview

## What This Project Does

WIIBBLE repurposes a Nintendo Wii Balance Board as a clinical force platform. Physiotherapists place the board in front of a screen, have the patient stand on it, and watch a live cursor track the patient's centre of pressure in real time. The tool also lets clinicians draw rehabilitation target circles on screen and record sessions to CSV for later analysis. It was built as part of the EPIC-Tech study at The University of Queensland / Griffith University / Princess Alexandra Hospital.

The key technical challenge is bridging a consumer gaming peripheral into a clinical workflow on a standard Windows PC. The board pairs over Bluetooth and exposes raw four-corner weight data as HID reports. WIIBBLE reads those 32-byte packets at ~120 fps, converts them to a screen position, and renders the result using an immediate-mode GPU renderer (DearPyGui) so the display never lags behind the sensor.

An intentional design constraint is that the app must run on computers that cannot have Python installed — clinicians get a single `.exe`. All business logic is in Python; a small C# DLL (`WiiBalanceBoardLibrary`) handles the one-time Bluetooth handshake that Windows requires before HID data flows.

For developer setup, build instructions, and running the app, see [DEV.md](DEV.md).

---

## Architecture Overview

The codebase is flat (all `.py` files in the repo root) and divided into six clear layers: entry point, session orchestration, UI rendering, input handling, sensor pipeline, and support utilities.

```mermaid
graph TD
    main["main.py<br/>(entry point)"]
    app["app.py<br/>(session & loop)"]
    ui["ui.py<br/>(all drawing)"]
    input["input.py<br/>(mouse handlers)"]
    dp["data_processing.py<br/>(sensor pipeline)"]
    state["state.py<br/>(AppState + Settings)"]
    calib["calibration.py<br/>(tare & calibration)"]
    board["board_connection.py<br/>(C# DLL bridge)"]
    mock["mock_board.py<br/>(hardware simulator)"]
    rec["recording.py<br/>(CSV output)"]
    ana["analysis.py<br/>(posturographic pipeline)"]
    cdpc["code_descriptors_postural_control"]

    main -->|"create_context\nload_fonts\ncreate_viewport"| app
    app -->|"draw calls"| ui
    app -->|"register handlers"| input
    app -->|"read / parse / filter"| dp
    app -->|"startup flow"| calib
    app -->|"save buffer"| rec
    app -->|"trigger analysis"| ana
    ana -->|"CoP features"| cdpc
    app -->|"read/write"| state
    calib -->|"measure_weight"| dp
    input -->|"session_state action"| app
    board -.->|"Bluetooth trigger\n(startup only)"| app
    mock -.->|"--mock flag"| app
```

`app.py` is the hub. It owns the session lifecycle and reaches into every other module, but it never draws — that is entirely delegated to `ui.py`. Input callbacks in `input.py` communicate back to `app.py` only through `session_state["action"]`, keeping the input layer decoupled from session logic. `data_processing.py` has no DPG or state imports at all — it is a pure functional pipeline that can be tested without any hardware or GUI.

---

## Key Data Flows

### 1. Live sensor → cursor on screen

Every frame, raw bytes from the board are transformed into a pixel position and rendered. This is the heartbeat of the application.

```mermaid
sequenceDiagram
    participant HID as HID Device
    participant dp as data_processing
    participant app as app.py
    participant ui as ui.py

    HID->>dp: read_data() → 32 bytes
    dp->>dp: parse_data() → corners (kg each)
    Note over dp,app: Raw corners stored in app_state.raw_corners (used for recording)
    dp->>dp: apply_filter() → smoothed corners (used for display only)
    dp->>dp: calculate_coordinates() → (raw_x, raw_y) px
    app->>app: apply zoom + pan offset → ball_x, ball_y
    app->>ui: draw_main_screen(ball_x, ball_y, trail, targets)
    ui->>ui: render to viewport_drawlist
```

### 2. Session startup (connect → tare → calibrate)

Before any data is shown, the board must be connected, zeroed, and the patient's body weight captured. This sequence runs once per session and is not skippable.

```mermaid
sequenceDiagram
    participant app as app.py
    participant bc as board_connection
    participant hid as hid.device
    participant calib as calibration
    participant dp as data_processing

    app->>bc: try_connection(dll_path)
    bc->>bc: load C# DLL, Connect(), Disconnect()
    bc-->>app: return 0 (success)
    app->>hid: device.open(VENDOR_ID, PRODUCT_ID)
    hid-->>app: open HID stream

    app->>calib: wait_for_tare(device, dl, app_state)
    calib->>dp: measure_weight() × 20 stable reads
    calib-->>app: board confirmed empty

    app->>dp: tare(device, data_struct)
    dp->>dp: average 10 reads → store baseline in data_struct

    app->>calib: sensitivity_calibration(device, dl, app_state)
    calib->>dp: measure_weight() until stable > baseline + 5 kg
    calib-->>app: calibrated body weight
```

### 3. Recording a session to CSV

A clinician starts a recording (with optional countdown), the app buffers force-deviation values each frame, and the buffer is flushed to a CSV file when recording stops.

```mermaid
sequenceDiagram
    participant cli as Clinician (toolbar)
    participant app as app.py
    participant dp as data_processing
    participant rec as recording.py

    cli->>app: click "Start Recording"
    app->>app: is_countdown=True, countdown_value=3
    loop Every second for 3 s
        app->>app: countdown_value -= 1
    end
    app->>app: is_recording=True, record_start=now

    loop Each frame while recording
        dp->>dp: parse_data() → raw corners (never filtered)
        app->>app: append (elapsed, x_kg, y_kg) to record_buffer
    end

    app->>app: elapsed >= record_duration → is_recording=False
    app->>rec: _save_recording_csv(buffer, weight, ui_filter_window)
    rec->>rec: write recordings/recording_YYYYMMDD_HHMMSS.csv
    Note over rec: # total_weight_kg, # ui_filter_window written as metadata comments

    alt duration ≥ 20 s
        app->>app: spawn background thread
        app->>ana: analyse_recording(csv_path)
        ana->>ana: load_recording() → parse CSV + metadata
        ana->>ana: to_cop_array() → CoP in cm (Leach 2014 Eq.1)
        ana->>cdpc: Stabilogram.from_array() → SWARII → 25 Hz + Butterworth
        cdpc->>ana: compute_all_features() → ~80-90 features
        ana->>ana: save recordings/features_YYYYMMDD_HHMMSS.json
    end
```

---

## Module Guide

| File / Module | Responsibility | Notes |
|---|---|---|
| `main.py` | DPG context, argparse, logging, screen-size detection | Deliberately thin — safe to import in tests; all logic guarded by `if __name__ == "__main__"` |
| `app.py` | Session lifecycle, render loop, recording state machine, action dispatch | The largest file; still being refactored (see TODO) |
| `ui.py` | Every DPG draw call — canvas, cursor, trail, targets, calibration screens, stats bar, toolbar | Never reads `AppState` directly during draws; receives values as arguments |
| `input.py` | Mouse click/drag/release/wheel handlers; target creation; Ctrl+pan; Ctrl+zoom | Communicates back to `app.py` only via `session_state["action"]` |
| `data_processing.py` | Raw HID read, byte parsing + tare, moving-average filter, coordinate calc, weight measurement | Pure functions — no DPG imports, no state; fully unit-testable |
| `calibration.py` | Tare detection and body-weight calibration blocking loops | Renders its own screens inline; calls `dpg.render_dearpygui_frame()` directly |
| `state.py` | `AppState` (runtime mutable state) + `Settings` (persisted preferences) | Settings auto-saved to `~/.wiibble/settings.json`; unknown fields silently ignored on load |
| `constants.py` | All magic numbers: hardware IDs, byte offsets, `SCALE_FACTOR`, thresholds, UI sizes | Single source of truth — never put literals in `app.py` or `ui.py` |
| `theme.py` | Colour palette, global DPG theme, font loading (FontAwesome + Roboto 100px) | `load_fonts()` must be called before `dpg.setup_dearpygui()` |
| `recording.py` | `_save_recording_csv()` — write buffer to timestamped CSV with body-weight + ui_filter_window metadata | Extracted from `app.py` specifically for testability |
| `analysis.py` | End-to-end posturographic pipeline: `load_recording()` → `to_cop_array()` → `Stabilogram` → `compute_all_features()` | Lazy-imports `code_descriptors_postural_control`; safe to use standalone. Auto-triggered by `app.py` for recordings ≥ 20 s. |
| `mock_board.py` | `MockHIDDevice` — drop-in for `hid.device()`, six named scenarios | Phase model (tare → step_on_stable → normal) mirrors real board calibration flow |
| `board_connection.py` | C# DLL loader via `pythonnet`; `try_connection()` triggers the Bluetooth handshake | Called once at startup then never again — all data flows through `hidapi` |
| `resources.py` | `resource_path()` — resolves asset paths in dev and Nuitka standalone builds | Pre-resolves common paths at import time; use this for all asset access |

**Boundary worth noting:** `board_connection.py` and `hid.device()` look like they do the same thing but serve entirely different purposes. The C# DLL is needed to trigger the OS-level Bluetooth handshake (a Nintendo quirk); once that succeeds and the DLL disconnects, `hidapi` opens the board as a plain HID device for all data. A developer who removes `board_connection.py` because "we're already using hidapi" will break real-hardware connects.

---

## State & Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Connecting : app starts

    Connecting --> ConnectionFailed : try_connection returns 1
    ConnectionFailed --> Connecting : Enter key pressed (retry)

    Connecting --> Tare : connection succeeded
    Tare --> Calibrating : board stable and empty (20 reads)
    Calibrating --> Running : stable body weight detected

    Running --> Running : each frame (sensor read → render)
    Running --> Recording : Start Recording clicked (after countdown)
    Recording --> Running : duration elapsed or Stop clicked

    Running --> Connecting : RESTART action
    Running --> [*] : window closed

    ConnectionFailed --> [*] : window closed
```

The toolbar and gear button are created at startup but hidden until `Calibrating → Running` transitions. This prevents clinicians from changing settings before a body weight is registered.

---

## Dependencies

| Package | Purpose | Why this one | Notes / risks |
|---|---|---|---|
| `dearpygui==2.1.1` | Immediate-mode GPU GUI | Redraws full canvas every frame — the natural model for real-time sensor data. `viewport_drawlist` gives true full-screen drawing. | **Pin strictly** — API breaks between minor versions. See [ADR-0001](decisions/0001-migrate-to-pyqt6.md) for migration proposal. |
| `hidapi==0.14.0.post2` | Read raw 32-byte HID reports from the board | Only Python library that reads raw HID without a kernel driver. Board exposes itself as a standard HID device after pairing. | |
| `pythonnet==3.0.3` | Load the C# DLL at runtime via `clr.AddReference()` | The Bluetooth handshake logic already existed in C# (WiiBalanceWalker lineage); `pythonnet` bridges it without a rewrite. | Must be 3.x — 2.x API is incompatible. |
| `numpy==1.24.4` | Array averaging in `tare()` | Used in one place only. | **Pinned to last version supporting Python 3.8** — can be relaxed if minimum Python version is raised. |
| `pytz` | Timezone-aware timestamps in filenames | Standard choice. | |
| `nuitka>=2.0` *(dev)* | Compile to standalone `.exe` | Produces a true compiled binary — fewer AV false-positives, faster startup, no Python runtime required on clinical machines. | |
| `pytest` / `pytest-cov` *(dev)* | Test runner + coverage | Standard. | Coverage gate ≥ 80% enforced in CI. |
| `ruff>=0.4` *(dev)* | Lint and format | Fast; configured in `pyproject.toml`. | Runs in CI. |

---

## Where to Start Reading

1. **`state.py`** — understand `AppState` and `Settings` first; almost every module touches them.
2. **`data_processing.py`** — the pure sensor pipeline; read alongside `constants.py`.
3. **`app.py / _run_session()`** — the main session flow from connection to render loop.
4. **`ui.py / draw_main_screen()`** — how the canvas is rendered each frame.
