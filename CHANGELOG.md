# Changelog

All notable changes to WIIBBLE are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Planned
- Move C# interop into dedicated `hardware_interface.py`
- Add `utils.py` for shared helpers
- Organise assets into `assets/fonts/`, `assets/images/` subfolders
- CI: Nuitka executable artifact on every push (manual [Build (develop)](.github/workflows/build-develop.yml) workflow available for QA)

---

## [2.1.0] — 2026-07-06

### Added
- In-app session report via `WIIBBLE-SessionReport.exe` companion when **generate report after recording** is enabled (default)
- `wiibble-session-report` CLI and `session_report/` package (launcher, runner, progress polling)
- Rectangular target placement (hold **R** + drag) and target repositioning
- Target hit counter with configurable dwell time (0–5 s)
- Quick-access canvas buttons: gear, clear screen, fit view, reset counter, record/stop
- Global and local axes display options in settings
- Axis flip (horizontal / vertical) for display and CSV recordings
- Manual body weight field and on-demand **Auto** / **Cal scale** board calibration in settings
- Recording filename prefix (shared across CSV, features JSON, and HTML report)
- Background sensor acquisition thread (`SensorAcquisition`) with latest-frame slot
- Typer-based CLIs (`wiibble`, `wiibble-process-recordings`, `wiibble-report`, `wiibble-session-report`)
- `session_actions.py` for UI-triggered settings mutations
- CI: `dotnet build` job for C# board library; `pip-audit` security job
- Linux mock-mode development documented in setup guide

### Changed
- Session lifecycle moved from `wiibble/app.py` to `wiibble/session.py` (`app.py` is now a thin re-export)
- Settings panel collapsible toggle; session restart button removed from UI
- CSV metadata extended with `flip_horizontal`, `flip_vertical`, and optional recording prefix in filenames
- Offline CLIs use configured `recording_dir` from settings; batch `--new` / `--all` modes for reports
- Documentation restructured under `docs/dev/` and `docs/user/` per project standards
- Version bumped to 2.1.0

### Fixed
- HID acquisition thread race during on-demand calibration (exclusive `stop()`/`start()`)
- Windows cursor stutter after background acquisition refactor
- Toast message formatting in session report progress UI
- Report path resolution for prefixed recordings
- Cross-platform Typer `--help` output

### Removed
- Cursor mode functionality
- Target jelly effect setting

---

## [2.0.2] — 2026-06-22

### Fixed
- HID acquisition thread race during on-demand calibration (exclusive `stop()`/`start()` instead of `pause()`/`resume()`)
- Windows cursor stutter after background acquisition refactor (non-blocking mode before thread start, latest-frame slot, redraw last frame when queue empty)
- Documentation: Windows settings path (`%APPDATA%\WIIBBLE\settings.json`), Nuitka output path (`dist_nuitka\wiibble.dist`), and troubleshooting `del` command

---

## [2.0.0] — 2026-05

### Added
- Posturographic feature extraction pipeline (`wiibble/analysis/analysis.py`): CoP conversion (Leach 2014) → SWARII resampling → Butterworth filter → ~80–90 features via `code_descriptors_postural_control`
- `wiibble-process-recordings` CLI for offline batch analysis
- HTML session report generation (`wiibble-report`) with Plotly/Jinja2: sway path, time series, velocity, PSD, diffusion, spatial density, feature table
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
- Analysis moved offline (`wiibble-process-recordings`) — removed from compiled app to keep Nuitka build fast and free of pandas/sklearn/statsmodels
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

## [1.0.0] — initial release

### Added
- Basic real-time CoP visualisation using Wii Balance Board via Bluetooth HID
- Tare and sensitivity calibration flow
- CSV recording with timestamp, x_kg, y_kg columns
- Mock mode (`--mock`, `--mock-scenario`) for hardware-free development and testing
- C# DLL bridge (`WiiBalanceBoardLibrary`) for Bluetooth handshake
- Nuitka-compiled standalone `.exe` with Inno Setup installer
