# ADR-001: Migrate UI Framework from DearPyGui to PyQt6/PySide6

**Date:** 2026-05-26
**Status:** Superseded by [ADR-004](004-dearpygui-realtime-ui.md)

## Context

WIIBBLE currently uses DearPyGui 2.1.1 as its immediate-mode GPU renderer. This was the right choice at project inception: it redraws the full canvas every frame (natural for real-time sensor data), `viewport_drawlist` gives true full-screen drawing, and it produces a single-file build with Nuitka.

However, as the project matures and the settings panel grows more complex, several DearPyGui limitations have become friction points:

- **Styling is severely constrained.** DearPyGui theming is limited to colour and font changes. Rounded panels, smooth transitions, and clinician-friendly layouts require hacks or are simply not achievable.
- **No panel animations.** The collapsible settings panel cannot animate smoothly, it snaps open/closed. This is a minor but visible quality gap vs clinical software peers.
- **Widget testing is not possible.** DearPyGui widgets cannot be instantiated headlessly, so UI logic cannot be unit-tested. Only the pure-pipeline modules (`wiibble/features/data_processing.py`, `wiibble/board/recording.py`, `wiibble/utils/state.py`) are currently testable.
- **Minor-version API breakage.** DearPyGui breaks its API between minor releases, requiring strict pinning and periodic migration effort.
- **Canvas drawing model.** The `viewport_drawlist` full-screen approach works, but `QPainter` on a `QWidget` with a `QTimer` driving updates is equivalent and more portable.

PyQt6/PySide6 addresses all of these while remaining a viable Nuitka/PyInstaller compilation target.

## Decision

*Not yet made. This ADR is in Proposed state pending team discussion and a prototype spike.*

The candidate decision is: **migrate the UI layer to PyQt6 (LGPL) or PySide6 (LGPL)**, keeping all non-UI modules (`wiibble/features/data_processing.py`, `wiibble/analysis/analysis.py`, `wiibble/board/recording.py`, `wiibble/utils/state.py`, `wiibble/board/board_connection.py`, `wiibble/board/mock_board.py`) completely unchanged.

## Migration Surface

| Current (DearPyGui) | Target (PyQt6/PySide6) |
|---|---|
| `viewport_drawlist` draw calls | `QPainter` on a `QWidget`, `QTimer` at ~100 Hz |
| DPG theme + font loading | QSS stylesheet |
| Collapsible settings panel | `QWidget` + `QPropertyAnimation` |
| `dpg.render_dearpygui_frame()` in calibration | Qt event loop + `QDialog` |
| Nuitka standalone build | PyInstaller bundle or Nuitka Qt bundle |
| No widget tests | `pytest-qt` for headless widget testing |

## Consequences

**Positive**

- Rich QSS styling, clinician-friendly, polished appearance
- `QPropertyAnimation`, smooth panel collapse/expand
- `pytest-qt`, headless widget testing, unblocking UI coverage
- Stable, mature API with strong long-term support
- Larger ecosystem of Qt-native components

**Negative**

- Non-trivial migration effort, all draw calls and layout code in `wiibble/ui/ui.py` must be rewritten
- `wiibble/ui/calibration_flow.py` inline frame rendering must be redesigned as proper Qt dialogs
- Build pipeline changes, Nuitka Qt bundle or switch to PyInstaller
- Team must learn Qt layout/signal-slot model
- Risk of introducing regressions in real-time rendering performance (requires benchmarking in spike)

## Spike Required Before Decision

Before committing, a prototype spike should:

1. Implement the main canvas + real-time cursor update using `QPainter` + `QTimer` at 100 Hz
2. Measure rendering latency vs current DearPyGui baseline (mock mode)
3. Implement the settings panel with `QPropertyAnimation` collapse
4. Confirm Nuitka or PyInstaller produces a working standalone `.exe`

## Related

- [TODO.md](../TODO.md) Phase 2 item (now tracked here)
- `wiibble/ui/ui.py` — primary migration target
- `wiibble/ui/calibration_flow.py` - secondary migration target
