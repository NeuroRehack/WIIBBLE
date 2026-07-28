# WIIBBLE User Manual

This manual is written for **clinicians and end users**. For developer setup, analysis pipelines, and report generation, see the [Developer Setup](../dev/setup.md).

---

## Main Interface

![WIIBBLE main screen](../../images/main_screen.png)
*Main screen: settings panel open on the left, live CoP cursor with sway trail on the canvas, weight and balance percentage in the stats bar at the bottom.*

The interface has three areas:

**Settings Panel** — Left side of the screen. Organised into sections: Recording, Cursor & Movement, Visualisation, and Calibration. Hidden by default when the session starts; open it with the gear button. Can be collapsed again with the gear button in the panel header or by clicking the canvas. When collapsed, a floating gear button remains in the top-left corner beside the other quick-access controls.

**Canvas** — The main area. Shows the live centre-of-pressure cursor, sway trail, targets, optional hit counter, and optional bounding box. All mouse interactions happen here.

**Stats Bar** — Bottom of the window. Shows left/right weight distribution percentage and total weight in kg. Colour reflects the amount of weight currently detected on the board.

**Quick Access** — Always-visible buttons on the canvas (once the session starts):

| Position | Buttons (panel collapsed) | Buttons (panel open) |
|---|---|---|
| Top-left | Gear, Clear Screen, Fit View, Reset Counter | Clear Screen, Fit View, Reset Counter (gear is in the panel header) |
| Top-right | Record / Stop | Record / Stop (over the recording indicator) |

These mirror the corresponding settings-panel controls so you can work without opening settings.

---

## Quick Access Buttons

**Gear** (top-left, panel collapsed) — Opens the settings panel. The same gear icon in the panel header closes it again.

**Clear Screen** (eraser icon) — Removes all targets and the sway trail from the canvas. Shortcut: **Ctrl+Shift+C**.

**Fit View** (expand icon) — Zooms and pans to fit all recorded movement within the view. Same as **Fit View to Bounding Box** in settings.

**Reset Counter** — Resets the target hit counter to zero. Same as **Reset hit counter** in settings.

**Record / Stop** (top-right) — Round red button when idle; turns square while recording or during the countdown. The configured duration limit (e.g. `00:10`, or `∞` for indefinite) is shown to the right of the button at all times; elapsed time appears on the left in a larger font while recording. Shortcut: **Ctrl+Space**.

---

## Settings Panel

### Gear Button

Opens and closes the settings panel. When collapsed, the floating gear button in the top-left corner reopens it.

### Recording

**Duration Presets** — Choose from 10 s, 20 s, 30 s, 60 s, or indefinite (∞). The active selection is highlighted.

**Manual Duration** — Type a custom duration in seconds (up to 3600). Enter `0` to record indefinitely until you press Stop.

**Start Recording / Stop Recording** — Starts a 3-second countdown then begins capturing. The button label toggles to **Stop Recording** while active. Click again to stop early.

**Save Location** — Shows the folder where recordings are saved (default: `Documents/WIIBBLE/recordings` under your home folder). Click the path to open it in your file manager, or use **Choose Folder…** to change it. The app remembers your choice between sessions.

**Prefix** — Optional filename prefix for CSV recordings, metrics JSON, and HTML reports (max 40 characters; letters, digits, underscores, and hyphens). Leave blank for the default `recording`. Example: `SPI001_SitStand` → `SPI001_SitStand_261101174543.csv`, `features_SPI001_SitStand_261101174543.json`, `report_SPI001_SitStand_261101174543.html`.

**Session report**

- **generate report after recording** (default on) — Builds an interactive HTML report when a recording ends.
- **Open in browser** (default on) — Opens the report in your default web browser when ready. Disabled when auto-report is off.
- A progress indicator appears while the report is being generated.
- **View last report** — Reopens the most recent report during the session.

### Cursor & Movement

**Cursor Size** — Adjusts the circle cursor radius (1–50 px). You can also drag the cursor on-screen to resize it.

**Sway Trail** — Controls how much movement history is visible: **None**, **Medium**, or **Long**.

**Smoothing Filter** — Number of frames averaged to smooth the cursor (1–20; 1 = no smoothing). Lower = more responsive; higher = smoother. This affects display only — recordings always save raw unfiltered data.

### Visualisation

**Zoom** — Adjusts the canvas zoom level. Also controllable with `Ctrl + Mouse Wheel`.

**Fit View to Bounding Box** — Automatically zooms and pans to fit all recorded movement on screen.

**Show bounding box** — Toggles the movement extent overlay on the canvas.

**Show global axes** — Toggles solid crosshairs at the screen centre (neutral stance reference).

**Show local axes** — Toggles dotted crosshairs centred on the sway bounding box, bounded to the box edges.

**Targets**

- **Dwell time (s)** — How long the cursor must stay inside a target before the hit counter increases (0–5 s in 0.1 s steps; 0 = instant).
- **Show hit counter** — Toggles the large centred number at the top of the canvas.
- **Reset hit counter** — Sets the counter back to zero.

**Flip axis**

- **Flip Vertical** — Inverts forward-back mapping on screen and in recordings.
- **Flip Horizontal** — Inverts left-right mapping on screen and in recordings.

### Calibration

**Body weight (kg)** — Patient reference weight for cursor normalization and CSV recordings. Defaults to 70 kg when not set. Valid range: 1–150 kg.

**Auto** — Runs step-off / step-on calibration to measure body weight on the board. Updates the body weight field when complete.

**Board reference (kg)** — Known mass (10–150 kg) placed on the board for hardware scale calibration. Use a certified weight (e.g. kettlebell, weight plates). Default: 20 kg.

**Cal scale** — Tares the board, prompts you to place the reference mass, then computes and saves the HID raw-to-kg scale factor for this board.

---

## Mouse & Keyboard Controls

### Mouse

| Action | Effect |
|---|---|
| Left-click cursor | Begin resizing cursor (drag to resize) |
| Left-click canvas (not cursor) | Start placing a new circular target; drag to set radius |
| Hold R + left-click drag | Place a rectangular target (click without dragging creates a default square sized to the cursor) |
| Left-click existing target | Begin moving it (drag to reposition) |
| Release | Finalise cursor size, new target, or target move |
| Right-click a target | Remove that target |
| Left-click canvas (settings panel open) | Collapse the settings panel |
| Ctrl + Left-click drag | Pan the canvas |
| Ctrl + Mouse Wheel | Zoom in/out around the pointer |

### Keyboard

| Key | Context | Effect |
|---|---|---|
| Enter | Connection failed screen | Retry board connection |
| Ctrl+Shift+C | Main session | Clear Screen (remove targets and sway trail) |
| Ctrl+Space | Main session | Start / Stop Recording |

Shortcuts are disabled while typing in a settings text field.

---

## Canvas Elements

**Cursor** — Filled circle representing the patient's current centre of pressure.

**Targets** — Circular or rectangular regions created on the canvas. Remain fixed to the movement space and scale with zoom. Drag to reposition; right-click to remove.

**Hit Counter** — Large number at the top of the canvas (when enabled). Increments when the cursor dwells inside a target for the configured dwell time.

**Sway Trail** — Fading history of recent movement.

**Bounding Box** — Dashed rectangle showing the extent of movement since last clear.

**Global Axes** — Solid grey crosshairs through the screen centre, marking the neutral board-centre reference.

**Local Axes** — Optional dotted crosshairs through the centre of the sway bounding box, spanning only within the box.

**Stats Bar** — Real-time left/right distribution and total weight.

**Recording Indicator** — Countdown and elapsed time during active recording.

---

## Recording Data

Starting a recording triggers a 3-second countdown, then captures data until the set duration elapses or you press Stop. The default recording duration is **30 seconds** (configurable in the settings panel). Recordings are saved as CSV files to the selected folder.

When **generate report after recording** is enabled (default on), WIIBBLE generates an interactive HTML report automatically when a recording ends and opens it in your web browser (if **Open in browser** is enabled). This usually takes a few seconds; progress is shown in the settings panel. Recordings of at least **20 seconds** include the full posturographic feature table; shorter recordings still show sway charts.

Use **View last report** in settings to reopen the most recent report during the session.

**CSV format:**
```
# total_weight_kg=71.2000
# ui_filter_window=5
# flip_horizontal=false
# flip_vertical=false
time (s),x (kg),y (kg)
0.000,0.123,-0.045
...
```

- `time` — elapsed seconds from recording start
- `x (kg)` — left-right force deviation (raw, unfiltered)
- `y (kg)` — front-back force deviation (raw, unfiltered)

The comment lines at the top record the patient body weight, display smoothing level, and axis-flip settings for traceability.

---

## Board Pairing

Pairing the Wii Balance Board to your computer over Bluetooth depends on your Bluetooth adapter type.

### Check your Bluetooth MAC address

Open a Command Prompt and run:
```
getmac /v /fo list
```
Find the Physical Address for your Bluetooth adapter.

### Case 1 — MAC address does NOT contain "00" (permanent pairing)

1. Download [WiiBalanceWalker v0.5](https://github.com/lshachar/WiiBalanceWalker/releases).
2. Open it and click **Add/Remove Bluetooth Wii device**.
3. Copy the **Permanent PIN Code**.
4. In Windows: **Settings → Bluetooth & devices → Add device**.
5. On the board: remove the battery cover and press the red button (blue LED blinks).
6. On the computer: select **Nintendo RVL-WBC-01**, click **Pair**, and paste the Permanent PIN.

This pairing persists — you do not need to repeat it each session.

### Case 2 — MAC address contains "00" (per-session pairing)

Permanent pairing is not supported by this adapter type. Pair each session via:
**Control Panel → Hardware and Sound → Devices and Printers**

You may need to remove and re-pair if you switch adapters or restart Windows.

---

## Connection & Calibration

On launch the app immediately attempts to connect to the board. If the board is unavailable, an error screen appears with instructions; press **Enter** to retry.

Once connected, the app checks for saved tare offsets:

- **First launch** (or after deleting settings): step off the board until the empty-board screen completes. The zero baseline is saved automatically.
- **Later launches**: saved offsets are applied immediately and the main canvas opens without the tare screen.

Body weight comes from **Settings → Calibration** (default 70 kg). You can type a weight manually or use **Auto** to measure it from the board.

**Auto** (body weight calibration) and **Cal scale** both run the empty-board tare step before measuring. Use either when you need to re-zero the board after moving it or when readings look offset. The **Tare saved** line in settings shows relative time (e.g. "just now") and updates as soon as the Step OFF phase completes, before step-on or reference-mass measurement.

Saved tare can drift over time (temperature, load-cell aging). Run **Auto** or **Cal scale** to refresh the zero baseline when weight or center-of-pressure readings look systematically wrong.

**Board scale calibration** (optional, per board): enter a known reference mass under **Board reference (kg)** and click **Cal scale**. This replaces the factory default HID conversion factor and is independent of patient body weight.

The settings panel (gear button) is available as soon as the main canvas appears.

---

## Tips

- Collapse the settings panel to maximise canvas space; click the canvas or the gear button to toggle it.
- Use **Fit View** or `Ctrl + Mouse Wheel` to focus on a specific area of movement.
- The app saves your preferences between sessions — zoom, save location, recording prefix, trail length, axis flips, target dwell time, tare offsets, and report options all persist.
- If the cursor feels jittery, increase the **Smoothing Filter** slider.
- If icons appear as boxes, check that `assets/fonts/fa-solid-900.ttf` is present.
- For a new patient, update body weight and use **Clear Screen**; quit and relaunch the app if you need to reconnect the board.

---

## Troubleshooting

| Symptom | Solution |
|---|---|
| Board does not connect | Ensure Bluetooth is on, board is paired, and the LED is blinking blue. Check battery level. Press **Enter** on the connection screen to retry. |
| DLL loading error | Make sure `WiiBalanceBoardLibrary.dll` is built. See [setup.md](../dev/setup.md). |
| Black screen / no canvas | Restart the app. Update graphics drivers if persistent. |
| Cursor very jittery | Increase the Smoothing Filter slider. |
| Gear icon missing | Check `assets/fonts/fa-solid-900.ttf` is present. |
| Settings lost | Delete `%APPDATA%\WIIBBLE\settings.json` (Windows) or `~/.wiibble/settings.json` (Linux/macOS) to reset to defaults. |
| Library error on startup | Run `uv sync` — see [setup.md](../dev/setup.md). |
| Report not generated | Ensure **generate report after recording** is enabled. Installed builds include the session-report companion; dev installs need `uv sync --extra analysis`. |

For developer and build issues see [setup.md](../dev/setup.md).

---

## Command-Line Options

```
wiibble [--mock] [--mock-scenario <scenario>]
```

| Flag | Description |
|---|---|
| `--mock` | Run with simulated data — no board required |
| `--mock-scenario <name>` | Choose simulation scenario: `sway` (default), `still`, `lean_left`, `lean_right`, `hands`, `step_on_off`, `calibration` |

These flags work with both `python -m wiibble` (`wiibble`) and the compiled `WIIBBLE.exe`.

---

## Posturographic Analysis & Reports

When **generate report after recording** is enabled (default), WIIBBLE generates an HTML report automatically at the end of each recording and opens it in your browser for review with the patient.

Each figure in the report (sway path, time series, velocity, PSD, diffusion plot, spatial density, feature table) is described in [Visualisation References](../dev/VISUALISATION_REFERENCES.md) with literature citations — useful when interpreting metrics with patients or in research write-ups.

For batch analysis of older recordings, or custom report paths, administrators can use the offline tools documented in [Developer Setup](../dev/setup.md#5-posturographic-analysis-and-reporting).
