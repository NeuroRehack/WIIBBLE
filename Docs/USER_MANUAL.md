# WIIBBLE User Manual

## Overview

WIIBBLE is a real-time visualization and recording tool for the Wii Balance Board, providing live feedback, calibration, and data recording. The interface is built with DearPyGui and is designed for both research and interactive use.

---

## Main UI Layout

- **Canvas Area:**  
  The main area displays your live center-of-pressure, targets, trails, and bounding box. All interactions (clicks, drags, zoom, pan) happen here.

- **Settings Panel:**  
  - Located on the left side of the screen.
  - Can be collapsed to a floating gear button in the top-left corner.


- **Stats Bar:**  
  - At the bottom of the window, shows left/right weight distribution and total weight.

---

## Settings Panel Controls

### Gear Button

- Opens and closes the left-hand settings panel.
- When the panel is collapsed, a floating gear button remains visible in the top-left.

### Session

- **Restart Session:**  
  - Restart the current session from recalibration.
  - This resets the connection and calibration flow.

### Recording

- **Duration Presets:**  
  - Quickly choose from 10s, 20s, 30s, 60s, or indefinite (∞).
  - The active preset is highlighted.

- **Manual Duration:**  
  - Type a custom duration in seconds.
  - Use `0` to record indefinitely.

- **Start Recording / Stop Recording:**  
  - Starts a recording session after a 3-second countdown.
  - Click again to stop recording early.
  - The current recording state is reflected in the button label.

- **Save Location:**  
  - Shows where recordings are saved.
  - Use **Choose Folder...** to change the output directory.

### Cursor & Movement

- **Cursor Toggle:**  
  - Switch between **Avatar** (person icon) and **Circle** cursor modes.
  - You can also click the on-screen cursor itself to toggle modes.

- **Cursor Size:**  
  - Adjust the circle cursor radius with the slider.
  - You can also drag the cursor directly on screen to resize it.

- **Sway Trail:**  
  - Choose how much movement history is shown: **None**, **Medium**, or **Long**.

- **Smoothing Filter:**  
  - Control how many frames are averaged to reduce noise.
  - Lower values are more responsive; higher values are smoother.

### Visualisation

- **Zoom:**  
  - Adjust the movement canvas zoom level.
  - The slider controls the overall zoom scale.

- **Fit View to Bounding Box:**  
  - Automatically zooms and pans to fit all recorded movement.

- **Show bounding box:**  
  - Toggle the movement bounding box overlay.

- **Target jelly effect:**  
  - Animate targets with a jelly wobble when they are hit.

- **Clear Screen:**  
  - Remove all targets and the sway trail from the canvas.

---

## Mouse & Keyboard Controls

### Mouse

- **Left Click on the canvas:**
  - If you click the cursor, the app begins a cursor drag operation.
  - If you click elsewhere, the app starts a new target at that location.

- **Drag after clicking on the canvas:**
  - Dragging from the cursor changes its size.
  - Dragging from the canvas creates a target radius in real time.

- **Release mouse button:**
  - Finalizes the cursor size or the new target.

- **Right Click on a target:**
  - Removes that target from the canvas.

- **Ctrl + Left Click & Drag:**
  - Pans the canvas.

- **Ctrl + Mouse Wheel:**
  - Zooms in and out around the mouse pointer.

### Keyboard

- **Enter (on connection failed screen):**
  - Retries the board connection.

---

## Canvas Features

- **Cursor:**  
  - Represents your current center-of-pressure.
  - Can be displayed as a circle or an avatar icon.

- **Targets:**  
  - Created by left-clicking and dragging on the canvas.
  - Targets scale with zoom and remain fixed relative to the movement space.

- **Trail:**  
  - Shows recent movement history.
  - Can be toggled between no trail, medium trail, or a long fading trail.

- **Bounding Box:**  
  - Displays the extent of movement on the canvas.

- **Stats Bar:**  
  - Shows real-time left/right weight distribution and total weight.

- **Recording Indicator:**  
  - Displays countdown and recording status when data is being captured.

---

## Data Recording

- **Start Recording:**  
  - Begins a recording after a short countdown.
  - Recording saves data to the selected folder.

- **Record Duration:**  
  - Use the preset buttons or enter a custom value.
  - Setting `0` records indefinitely until you stop it.

- **Save Location:**  
  - Choose where CSV output is stored.
  - The app remembers the selected folder between sessions.

- **CSV Format:**  
  - Columns: `time (s)`, `x (kg)`, `y (kg)`
  - Time is relative to the start of recording, and x/y are displacement values in kg.

---

## Connection & Calibration

- **Startup:**  
  - The app attempts to connect to the Wii Balance Board on launch.
  - If the board is unavailable, follow the on-screen troubleshooting instructions.

- **Tare & Calibration:**  
  - The app guides you through taring (zeroing) and setting sensitivity before the main screen appears.

---

## Tips

- **Collapse the settings panel** to maximize canvas space; reopen it with the floating gear button.
- **Use the zoom slider** or `Ctrl+Mouse Wheel` to zoom in on movement details.
- **Use the target controls** for training tasks or visual feedback exercises.
- **The app saves settings** between sessions so your preferences persist.

---

## Troubleshooting

- If the board does not connect, ensure Bluetooth is enabled, the board is paired, and powered on.
- Use the mock mode (`--mock`) for testing without hardware.

**Cursor feels jittery**
- Increase the **Filter** slider in the settings panel.

**Cannot see the gear icon**
- Make sure the font file `assets/fonts/fa-solid-900.ttf` is present.

---

## Command-Line Options

- `--mock`  
  Run with simulated data (no hardware required).
- `--mock-scenario sway|still|lean_left|lean_right|hands|step_on_off`  
  Choose the mock data scenario.

> Note: these same flags also work with the compiled executable in `outputBuild\WIIBBLE\WIIBBLE.exe`.


