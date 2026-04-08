# WIIBBLE — Architecture Overview

This document describes WIIBBLE's main architectural components, how they interact, and where the core logic lives.

## 1. High-level architecture

WIIBBLE is a desktop application built on Python and DearPyGui, with optional hardware integration through `pythonnet` and a .NET C# library.

- `main.py` — entry point: sets up logging, DearPyGui, argument parsing, app state, and starts the main run loop.
- `app.py` — application lifecycle and main rendering/logic loop.
- `ui.py` — all UI layout, screen rendering, canvas drawing, and input handling.
- `theme.py` — colors, global styling, font loading, and icon support.
- `data_processing.py` — sensor parsing, filtering, coordinate calculations, and weight computation.
- `calibration.py` — tare and sensitivity calibration workflows.
- `state.py` — `Settings` persistence and runtime `AppState`.
- `resources.py` — resource path resolution for dev and standalone builds.
- `mock_board.py` — simulated balance board input for development.
- `board_connection.py` — hardware bridge via `pythonnet` to the C# DLL.
- `WiiBalanceBoardLibrary/` — C# project producing the DLL used for real board communication.

## 2. Data flow

1. **Input source**
   - Real board: `board_connection.py` loads the C# DLL and reads HID reports.
   - Mock board: `mock_board.py` generates simulated sensor values.

2. **Raw data acquisition**
   - `read_data()` in `data_processing.py` returns a raw 32-byte report.

3. **Parsing and tare correction**
   - `parse_data()` extracts the four corner sensor values.
   - `tare()` corrects baseline offsets.

4. **Filtering**
   - `apply_filter()` smooths the corner values with a moving average.

5. **Force deviation / coordinates**
   - `calculate_force_deviation_kg()` computes x/y balance deviations.
   - `calculate_coordinates()` converts those deviations into screen coordinates.

6. **UI rendering**
   - `ui.py` draws the cursor, trail, targets, and calibration screens.
   - Theme and fonts are applied via `theme.py`.

7. **Recording**
   - During recording, the app buffers timestamps and coordinates.
   - `_save_recording_csv()` writes CSV files to `recordings/`.

## 3. Main runtime flow

`main.py` does the following:

1. Parse CLI args (`--mock`, `--mock-scenario`).
2. Create DearPyGui context.
3. Load settings via `state.Settings.load()`.
4. Determine screen size using `ctypes`.
5. Initialize app state and history buffer.
6. Load fonts and start DearPyGui.
7. Create viewport and show it.
8. Call `run()` from `app.py`.
9. On exit, destroy DearPyGui context.

## 4. Build and packaging

- Packaging is currently done with Nuitka via `compiler.bat`.
- `pyproject.toml` is used for dependency management with `uv`.
- `Docs/SETUP.md` describes the build steps for both dev and standalone builds.

## 5. Resource loading

`resources.py` resolves paths for two modes:

- Development: resources are loaded from repository paths.
- Standalone build: resources are loaded from the exe directory.

This supports the compiled executable in `outputBuild\WIIBBLE`.

## 6. Hardware integration

- `board_connection.py` uses `clr` and `pythonnet` to load the C# assembly.
- It instantiates `WiiBalanceBoardLibrary.BalanceBoardManager`.
- Connection, disconnect, and event handling occur through the managed assembly.

## 7. Mock support

- `MockHIDDevice` in `mock_board.py` mimics board data streams.
- It is selected when `--mock` is passed.
- Mock scenarios are designed to exercise calibration and movement logic.

## 8. Key design notes

- The UI and data pipeline are separated: `app.py` orchestrates, `ui.py` renders, and `data_processing.py` computes values.
- Runtime state is centralized in `AppState` and persisted via `Settings`.
- Logging is configured in `main.py` before importing application modules.
- Fonts are loaded before `dpg.setup_dearpygui()` in `theme.py`.

## 9. Future architecture improvements

- Split `app.py` into smaller modules: `recording.py`, `session.py`, `input.py`.
- Move C# interop into `hardware_interface.py`.
- Add automated tests for `data_processing.py` and `state.py`.
- Add CI workflows to verify build and run steps.
