# WIIBBLE — Setup Guide

This guide covers everything needed to get WIIBBLE running on a fresh Windows
machine, from installing prerequisites through to running the app with a real
Wii Balance Board.

---

## Prerequisites

You will need the following installed before starting:

| Requirement | Version | Notes |
|---|---|---|
| Windows | 10 or 11 | Required for Bluetooth HID |
| Python | 3.10+ recommended (3.8+ minimum) | [python.org](https://www.python.org/downloads/) |
| .NET 8.0 SDK | Latest | [dotnet.microsoft.com](https://dotnet.microsoft.com/en-us/download) |
| .NET Framework 4.8 | Included on Win 10/11 | Check: `reg query "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full" /v Release` |
| Git | Any recent version | [git-scm.com](https://git-scm.com/) |
| uv | Latest | Package manager — see below |
| Bluetooth adapter | Must be built-in or USB dongle | See [Board Pairing](#board-pairing) in ReadMe.md |

---

## Step 1 — Install uv

`uv` is a fast Python package manager that replaces pip for this project.
Open a PowerShell terminal and run:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Verify the install:

```powershell
uv --version
```

You should see something like `uv 0.x.x`.

> **Why uv?** It resolves and installs all dependencies in seconds,
> handles virtual environments automatically, and generates a lockfile
> (`uv.lock`) so everyone gets identical package versions.

---

## Step 2 — Clone the repository

```powershell
git clone https://github.com/NeuroRehack/WIIBBLE.git
cd WIIBBLE
git checkout develop
```

---

## Step 3 — Create the virtual environment and install dependencies

```powershell
uv sync
```

This does three things automatically:
1. Creates a `.venv` folder in the project directory
2. Installs all runtime dependencies from `pyproject.toml`
3. Writes a `uv.lock` file pinning exact versions

To also install developer tools (linting, testing, packaging):

```powershell
uv sync --extra dev
```

> **Note:** You do not need to activate the virtual environment manually.
> All `uv run` commands below use it automatically. If you want to activate
> it for an interactive session: `.venv\Scripts\activate`

---

## Step 4 — Build the C# library

WIIBBLE communicates with the balance board via a C# DLL.
Build it once before running the app:

```powershell
cd WiiBalanceBoardLibrary
dotnet build
cd ..
```

A successful build prints something like:
```
Build succeeded.
    0 Warning(s)
    0 Error(s)
```

The DLL is placed in `WiiBalanceBoardLibrary\bin\Debug\net48\WiiBalanceBoardLibrary.dll`.
`board_connection.py` resolves this path automatically.

---

## Step 5 — Verify the setup with mock mode

Before involving hardware, confirm the app runs correctly using the built-in
simulator:

```powershell
uv run python main.py --mock --mock-scenario sway
```

You should see the connection and calibration screens, then the main canvas with
a cursor moving in a slow sway pattern. If this works, your Python environment
and all dependencies are correctly installed.

Other available scenarios:

```powershell
uv run python main.py --mock --mock-scenario still
uv run python main.py --mock --mock-scenario lean_left
uv run python main.py --mock --mock-scenario lean_right
uv run python main.py --mock --mock-scenario hands
```

---

## Step 6 — Pair the Wii Balance Board

See the **Board Pairing** section in `ReadMe.md` for full instructions.
The short version:

1. Run `getmac /v /fo list` in a command prompt and check your Bluetooth
   adapter's Physical Address.
2. **If the MAC address contains "00"** → pair via
   `Control Panel → Hardware and Sound → Devices and Printers` each session.
3. **If the MAC address does not contain "00"** → use WiiBalanceWalker v0.5
   to generate a permanent PIN and pair once permanently.

---

## Step 7 — Run with the real board

1. Ensure the board is paired and the blue LED is blinking.
2. Run:

```powershell
uv run python main.py
```

---

## Step 8 — Build a standalone executable (optional)

This produces a self-contained `outputBuild\WIIBBLE\` folder that can be
copied to a clinical machine without Python installed.

> Requires dev dependencies: `uv sync --extra dev`

```powershell
.\compiler.bat
```

The compiled exe is placed in `outputBuild\WIIBBLE\WIIBBLE.exe`.
Mock mode works with the compiled exe too:

```powershell
outputBuild\WIIBBLE\WIIBBLE.exe --mock --mock-scenario sway
```

The build tool is [Nuitka](https://nuitka.net/). It compiles Python to C and
bundles all dependencies, including the native DearPyGui extension, without
the DLL path issues that affected PyInstaller.

3. Follow the on-screen instructions:
   - **Connection screen** — app searches for the board automatically.
   - **Tare screen** — board must be empty. App measures the baseline.
   - **Calibration screen** — step onto the board and stand still when prompted.

    - **Main canvas** — live cursor, weight stats, and balance bar are now active.
    - **Recording:**
       - Set the desired recording duration in the toolbar.
       - Click **Start Recording** to begin. A short countdown will start.
       - The button changes to **Stop Recording** while recording is active. Click it to stop early, or let the timer run out.
       - After recording, a CSV file is saved automatically in the `recordings/` folder (e.g., `recording_YYYYMMDD_HHMMSS.csv`).
       - The recording feature works in both real and mock modes.

---

## Application controls

| Control | Action |
|---|---|
| button (top-left) | Collapse / expand the settings toolbar |
| **RESTART** | Return to the connection screen |
| **RESET SCREEN** | Clear trail, targets, and bounding box |
| **Start/Stop Recording** | Begin or end a recording session; saves data to CSV in `recordings/` |
| **Trail** combo | Set trail length: None / Medium / Long |
| **Filter** slider | Moving average smoothing (1 = off, 30 = max smooth) |
| **Zoom** slider | Scale the cursor movement range |
| **Auto-Scale** | Zoom to fit the recorded bounding box on screen |
| Click on cursor | Toggle between avatar and circle cursor |
| Click on canvas | Place a target circle |

---

## Troubleshooting

**App crashes on startup with a DLL error**
- Confirm you ran `dotnet build` in Step 4.
- Check that `.NET Framework 4.8` is installed.
- Try running from a terminal (not double-click) to see the full error.

**`uv sync` fails**
- Make sure Python 3.8+ is installed and on your PATH: `python --version`
- Try `uv python install 3.11` to let uv manage the Python version itself.

**Board not found**
- Confirm Bluetooth is enabled and the board LED is blinking blue.
- Try removing and re-pairing the board.
- Check battery level — low batteries cause connection failures.

**Cursor is very jittery**
- Increase the **Filter** slider in the settings toolbar.
- Values around 5–15 frames work well for most clinical scenarios.

**Black screen / no canvas**
- This can happen if the DPG window fails to initialise. Try closing and
  restarting. If it persists, check your graphics drivers are up to date.

**Font shows as `[=]` instead of a gear icon**
- Confirm `assets/fonts/fa-solid-900.ttf` exists in the project folder.
- This file is vendored in the repository — if it is missing, re-clone or
  copy it from another machine.

---

## File structure (key files)

```
WIIBBLE/
├── main.py                  # Entry point
├── app.py                   # Session lifecycle and main loop
├── ui.py                    # All canvas and screen rendering
├── theme.py                 # Colours, DPG theme, font loading
├── data_processing.py       # Sensor reading, filtering, coordinates
├── calibration.py           # Tare and sensitivity calibration
├── state.py                 # AppState and Settings dataclasses
├── constants.py             # Hardware constants
├── resources.py             # Path resolution (dev + PyInstaller)
├── mock_board.py            # Hardware simulator for development
├── board_connection.py      # C# DLL bridge via pythonnet
├── assets/
│   └── fonts/
│       └── fa-solid-900.ttf # FontAwesome 5 Solid (OFL-1.1, vendored)
├── WiiBalanceBoardLibrary/  # C# project — must be built before running
├── pyproject.toml           # Dependencies and tooling config
├── CHANGELOG.md             # Full history of changes
└── ReadMe.md                # Project overview and board pairing guide
```

---

## Settings file

User preferences are automatically saved to:

```
.wiibble\settings.json
```

Delete this file to reset all settings to defaults. The file is created
automatically on first run.
