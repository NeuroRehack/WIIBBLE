![CI](https://github.com/NeuroRehack/WIIBBLE/actions/workflows/ci.yml/badge.svg)
![Coverage](https://img.shields.io/badge/coverage-%E2%89%A580%25-brightgreen)
![License](https://img.shields.io/github/license/NeuroRehack/WIIBBLE)
![Platform](https://img.shields.io/badge/platform-Windows-blue)
![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)

> ⚠️ **Note**: Only Python 3.11 or 3.12 are supported. Python 3.13 and 3.14 are NOT supported due to pythonnet incompatibility. Download 3.12.x from [python.org](https://www.python.org/downloads/).

# WIIBBLE — Wii Balance Board Live Environment

<div align="center">
  <img src="./images/logoPerson.png" alt="WIIBBLE Logo" width="400">
</div>

---

WIIBBLE repurposes the Nintendo Wii Balance Board as a clinical force platform. Physiotherapists place the board in front of a screen, have the patient stand on it, and see a live cursor track their centre of pressure in real time. Sessions are recorded to CSV, and an optional in-app HTML report summarises posturographic features at the end of each recording.

Built as part of the **EPIC-Tech study** at The University of Queensland / Griffith University / Princess Alexandra Hospital.

**Hardware:** Nintendo Wii Balance Board (RVL-WBC-01) with a Windows PC that has Bluetooth (built-in or USB adapter). Pair the board before launching the app — see [Board Pairing](docs/user/manual.md#board-pairing).

---

<div align="center">
  <img src="./images/main_screen.png" alt="WIIBBLE main screen, settings panel open, sway trail visible" width="780">
  <br><em>Main screen: collapsible settings panel (left), real-time CoP cursor with sway trail (canvas), weight and balance stats (bottom bar).</em>
</div>

---

## Features

- Real-time centre-of-pressure visualisation with sway trail
- Circular and rectangular rehabilitation targets with hit counter and dwell time
- Sensitivity calibration, tare, and per-board scale calibration
- Session recording to CSV (raw, unfiltered) with optional filename prefix
- In-app HTML session report via companion process (Plotly; auto-generated when enabled)
- Offline posturographic analysis: ~80–90 features (ellipse area, velocity, PSD, fractal dimension, SDA…)
- Bluetooth connection via standard Windows pairing
- Single `.exe` for clinical machines, no Python required

---

## Quick start

1. **Download the latest release** from the [Releases page](https://github.com/NeuroRehack/WIIBBLE/releases).
2. **Pair your Wii Balance Board**, see [Board Pairing](docs/user/manual.md#board-pairing) in the User Manual.
3. **Run WIIBBLE.exe**, follow the on-screen calibration steps, then use the settings panel to start recording.

For full usage instructions see the [User Manual](docs/user/manual.md).

---

## Documentation

| Document | Audience | Contents |
|---|---|---|
| [User Manual](docs/user/manual.md) | Clinicians | Interface, pairing, recording, reports |
| [Developer Setup](docs/dev/setup.md) | Developers | Bootstrap, test, build, packaging |
| [Architecture](docs/dev/architecture.md) | Developers | Layers, data flows, design decisions |
| [Data Pipeline](docs/dev/DATA_PIPELINE.md) | Developers | Sensor → CSV → features → report |
| [Visualisation References](docs/dev/VISUALISATION_REFERENCES.md) | Developers | Literature basis for report figures |
| [Changelog](CHANGELOG.md) | All | Version history |
| [Contributing](CONTRIBUTING.md) | Developers | Branching, style, PR process |

---

## Development

```powershell
git clone https://github.com/NeuroRehack/WIIBBLE.git
cd WIIBBLE
just sync
uv run python -m wiibble --mock --mock-scenario sway
```

Mock mode simulates a live board with no hardware required. On Linux, mock mode supports full UI development; real hardware and packaging remain Windows-only.

---

## License

This project is licensed under the [GNU General Public License v3.0](LICENSE).
© 2026 NeuroRehack. See the LICENSE file for details.
