# Changelog

All notable changes to WIIBBLE are documented here.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).  
Versions follow [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Planned
- Manual board recalibration option (adjustable `SCALE_FACTOR` per board)
- Further refactor of `wiibble/app.py` into `wiibble/session.py`
- Move C# interop into dedicated `hardware_interface.py`
- Add `utils.py` for shared helpers
- Organise assets into `assets/fonts/`, `assets/images/` subfolders
- CI: dotnet build workflow
- CI: Nuitka executable artifact

---

## [2.x.0] — current

### Added
- Posturographic feature extraction pipeline (`wiibble/analysis/analysis.py`): CoP conversion (Leach 2014) → SWARII resampling → Butterworth filter → ~80–90 features via `code_descriptors_postural_control`
- `process_recordings.py` CLI for offline batch analysis
- HTML session report generation (`report.py`) with Plotly/Jinja2: sway path, time series, velocity, PSD, diffusion, spatial density, feature table
- `VISUALISATION_REFERENCES.md` — literature justification for every report figure
- Left-side collapsible settings panel replacing horizontal toolbar (sections: Session, Recording, Cursor & Movement, Visualisation)
- Countdown timer displayed during recording
- Off-centre zoom (Ctrl + Mouse Wheel around pointer)
- Sensitivity slider in settings panel
- Custom font rendering (FontAwesome + Roboto) replacing blurry DPG text
- Resizable target spots
- `recordings/features_*.json` auto-generated for sessions ≥ 20 s
- GitHub Actions CI: ruff lint + pytest with ≥ 80% coverage gate

### Changed
- Decoupled UI smoothing filter from recorded data — CSV always contains raw unfiltered values; `ui_filter_window` stored as provenance metadata only
- Analysis moved offline (`process_recordings.py`) — removed from compiled app to keep Nuitka build fast and free of pandas/sklearn/statsmodels
- Stats bar colour now dynamic based on weight on board
- Settings panel and gear button hidden until calibration completes

### Fixed
- Settings button no longer appears on tare/calibration/connection screens
- Settings bar no longer disappears on screen resize or when switching windowed ↔ fullscreen
- Settings bar no longer crops on smaller screens
- Spurious red marker on settings bar click removed

### Refactored
- Recording logic extracted from `wiibble/app.py` into `wiibble/board/recording.py` for testability
- `wiibble/app.py` large code blocks broken into smaller functions
- `print()` calls replaced with `logging` module (DEBUG/INFO/ERROR); log at `~/.wiibble/wiibble.log`

---

## [1.x.0] — initial release

- Basic real-time CoP visualisation using Wii Balance Board via Bluetooth HID
- Tare and sensitivity calibration flow
- CSV recording with timestamp, x_kg, y_kg columns
- Mock mode (`--mock`, `--mock-scenario`) for hardware-free development and testing
- C# DLL bridge (`WiiBalanceBoardLibrary`) for Bluetooth handshake
- Nuitka-compiled standalone `.exe` with Inno Setup installer
