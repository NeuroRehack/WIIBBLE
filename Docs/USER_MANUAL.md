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

## Board Pairing

Pairing the Wii Balance Board to your computer over Bluetooth can vary depending on your device's Bluetooth adapter.

### Check your Bluetooth MAC address
- Open a command prompt and type:
  ```
  getmac /v /fo list
  ```
  Look for the Physical Address of your Bluetooth adapter.

### Case 1: Bluetooth MAC address **does NOT** contain "00"
- Permanent pairing is possible:
  1. Download WiiBalanceWalker v0.5 from [here](https://github.com/lshachar/WiiBalanceWalker/releases).
  2. Open it and click `Add/Remove Bluetooth Wii device`.
  3. Copy the Permanent PIN Code.
  4. In Windows: Settings ➔ Bluetooth & devices ➔ Add device.
  5. On the board: Remove battery cover, press red button (blue light should blink).
  6. On the computer: Select `Nintendo RVL-WBC-01` ➔ Pair ➔ paste Permanent PIN.

### Case 2: Bluetooth MAC address **does** contain "00"
- Permanent pairing may not be supported. Pair **each session** via:
  - Control Panel ➔ Hardware and Sound ➔ Devices and Printers
  - You may need to remove and re-pair if you switch Bluetooth adapter or restart.

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

If you have trouble:
- **Board does not connect**: Ensure Bluetooth is enabled, the board is paired, and powered on.
- **Mock mode**: Use `--mock` for testing without hardware.
- **Library Issues**: If the application fails to run due to library problems, try installing the required packages one at a time (`uv sync`, see DEV.md).
- **Connection Issues**: If the application fails to connect to the Wii Balance Board, check:
    - Bluetooth is enabled
    - Board is correctly paired and LED is blinking blue
    - Battery level is sufficient (replace batteries if in doubt)
- **DLL Loading Issues**: Ensure `WiiBalanceBoardLibrary.dll` is built and is in the location required by `board_connection.py`.

**Cursor feels jittery**
- Increase the **Filter** slider in the settings panel.

**Cannot see the gear icon**
- Make sure the font file `assets/fonts/fa-solid-900.ttf` is present.

For more, see [Developer Setup & Workflow Guide](DEV.md)

---

## Command-Line Options

- `--mock`  
  Run with simulated data (no hardware required).
- `--mock-scenario sway|still|lean_left|lean_right|hands|step_on_off`  
  Choose the mock data scenario.

> Note: these same flags also work with the compiled executable in `outputBuild\WIIBBLE\WIIBBLE.exe`.

---

## Posturographic Analysis: Analyzing Session Recordings


After you record balance data, you can extract clinically-relevant posturographic features from your CSVs. This post-processing is done outside the app using a command-line tool. 

**What you need:**
- Make sure analysis dependencies are installed (**see installation steps in [DEV.md](DEV.md), "Development Workflow"**).

### Typical Analysis Tasks

**Analyze all new (unanalyzed) recordings in `recordings/`:**
```powershell
python process_recordings.py --new
```

**Analyze a specific recording:**
```powershell
python process_recordings.py recordings/recording_YYYYMMDD_HHMMSS.csv
```

**Re-analyze (overwrite) all recordings:**
```powershell
python process_recordings.py --all
```

**Where does the output go?**
- Results are written as `.json` files beside the original CSVs (e.g.,
  `recordings/features_YYYYMMDD_HHMMSS.json`).
- Each file contains ~80-90 posturographic features plus provenance (patient weight, smoothing, etc).

**Tip:** If you get an error about missing packages, make sure to install analysis dependencies as described in [DEV.md](DEV.md).

**For a technical explanation of each analysis step and data flow, see [DATA_PIPELINE.md](DATA_PIPELINE.md)**.

## Session Reports (HTML)

WIIBBLE can generate a detailed HTML summary report for each session, viewable in any web browser or saved as PDF for clinical records. These reports show all analysis figures and a full numerical feature table.

- Reports appear in your data folder (`recordings/`).
- Ask your clinic IT, administrator, or advanced user to generate these if you do not see them automatically.
- For technical instructions on running or customizing the reporter, see [Data Pipeline](DATA_PIPELINE.md#9-report-generation) or [Developer Guide](DEV.md#report-generation-html-plotly).

Each plot includes a neutral caption describing what is displayed.

