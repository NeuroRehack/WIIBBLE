# WIIBBLE User Manual

## Overview

WIIBBLE is a real-time visualization and recording tool for the Wii Balance Board, providing live feedback, calibration, and data recording. The interface is built with DearPyGui and is designed for both research and interactive use.

---

## Main UI Layout

- **Canvas Area:**  
  The main area displays your live center-of-pressure, targets, trails, and bounding box. All interactions (clicks, drags, zoom, pan) happen here.

- **Toolbar (Control Panel):**  
  - Located at the top of the window (can be collapsed to a floating gear button, top left).
  - Contains all controls for session management, visualization, and settings.

- **Stats Bar:**  
  - At the bottom of the window, shows left/right weight distribution and total weight.

---

## Toolbar Buttons & Controls

- **Gear Button:**  
  - Expands/collapses the full toolbar.

- **RESTART:**  
  - Restarts the session, reconnecting to the board and resetting all state.

- **RESET SCREEN:**  
  - Clears all targets and resets pan/zoom to defaults.

- **Record Duration (s):**  
  - Set the duration (in seconds) for the next recording.

- **Start Recording / Stop Recording:**  
  - Begins or ends a timed data recording.  
  - Shows a 3 seconds countdown before starting.  
  - Data is saved as a CSV in the `recordings/` folder.

- **Cursor Toggle:**  
  - Switches between “Avatar” (person icon) and “Circle” cursor modes.

- **Trail:**  
  - Choose how much of your movement history is shown (None, Medium, Long).

- **Filter:**  
  - Adjusts the moving average window for the live data (higher = smoother, more lag).

- **Zoom:**  
  - Adjusts the zoom level of the canvas.  
  - Can also be controlled with Ctrl+Mouse Wheel.

- **Auto-Scale:**  
  - Automatically zooms to fit all movement data in view.

- **Sensitivity:**  
  - Adjusts how much the cursor moves for a given weight shift.

- **Reset Pan:**  
  - Centers the canvas (removes any panning).

---

## Mouse & Keyboard Controls

### Mouse

- **Left Click (Canvas):**
  - If clicking on the cursor: toggles cursor mode.
  - Else: starts creating a new target at the clicked location.
    - **Drag while holding:** Sets the radius of the new target in real time.
    - **Release:** Finalizes the target with the chosen size.

- **Ctrl + Left Click & Drag (Canvas):**
  - Pans the canvas in any direction.

- **Ctrl + Mouse Wheel (Canvas):**
  - Zooms in/out, anchored at the mouse position (the content under the mouse stays fixed).

### Keyboard

- **Enter (on connection failed screen):**
  - Retries connecting to the Wii Balance Board.

---

## Canvas Features

- **Cursor:**  
  - Shows your current center-of-pressure.  
  - Can be a circle or a person icon (toggle in toolbar).

- **Targets:**  
  - User-defined circles placed by clicking and dragging on the canvas.
  - Each target has a customizable radius (set by drag distance).
  - Targets scale with zoom and remain fixed relative to the content.

- **Trail:**  
  - Shows your recent movement history as a fading path.

- **Bounding Box:**  
  - Outlines the extents of your movement.

- **Stats Bar:**  
  - Displays left/right weight distribution and total weight in real time.

- **Countdown & Recording Indicator:**  
  - Shows a countdown before recording starts.
  - Displays a red “REC” indicator and timer during recording.

---

## Data Recording

- **Start Recording:**  
  - Initiates a countdown, then records for the set duration.
  - Data is saved as a CSV file in the `recordings/` directory.

- **CSV Format:**  
  - Columns: `time (s)`, `x (kg)`, `y (kg)`
  - Time is relative to the start of recording, and x/y are the displacements from the center in kg

---

## Connection & Calibration

- **Startup:**  
  - Prompts for connection to the Wii Balance Board.
  - If connection fails, shows troubleshooting steps and allows retry.

- **Tare & Calibration:**  
  - Guides you through taring (zeroing) and sensitivity calibration before main use.

---

## Tips

- **Toolbar can be collapsed** to maximize canvas space; use the floating gear to reopen.
- **Zoom and pan** allow you to focus on any region of interest.
- **Targets** can be used for training, games, or research tasks.
- **All settings** are saved between sessions.

---

## Troubleshooting

- If the board does not connect, ensure Bluetooth is enabled, the board is paired, and powered on.
- Use the mock mode (`--mock`) for testing without hardware.

**Cursor is very jittery**
- Increase the **Filter** slider in the settings toolbar.

**Font shows as `[=]` instead of a gear icon**
- Confirm `assets/fonts/fa-solid-900.ttf` exists in the project folder.
- This file is vendored in the repository — if it is missing, re-clone or copy it from another machine.

---

## Command-Line Options

- `--mock`  
  Run with simulated data (no hardware required).
- `--mock-scenario sway|still|lean_left|lean_right|hands|step_on_off`  
  Choose the mock data scenario.

> Note: these same flags also work with the compiled executable in `outputBuild\WIIBBLE\WIIBBLE.exe`.


