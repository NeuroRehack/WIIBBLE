# ADR-004: DearPyGui for Real-Time UI

**Date:** 2026-07-06
**Status:** Accepted

## Context

WIIBBLE must render a full-screen canvas at ~100 Hz with a live centre-of-pressure cursor, sway trail, clinician-placed targets, and a collapsible settings panel. Latency between sensor input and on-screen cursor must be imperceptible during rehabilitation tasks.

Traditional retained-mode GUI frameworks redraw only changed widgets. WIIBBLE's primary view is a custom-drawn canvas that updates every frame — an immediate-mode model fits naturally.

The application must compile to a standalone Windows `.exe` via Nuitka for deployment on clinical machines without Python installed.

## Decision

Use **DearPyGui 2.1.1** as the UI framework. All canvas elements are drawn each frame onto a `viewport_drawlist`. Settings controls are DPG widgets overlaid on the viewport. The main loop in `session.py` calls `draw_main_screen()` every frame after processing the latest sensor sample.

## Consequences

**Positive**

- Immediate-mode redraw matches the sensor-driven update model
- `viewport_drawlist` provides true full-viewport drawing without embedding a separate graphics context
- Single-process architecture — no IPC between sensor and renderer
- Nuitka produces a working standalone binary with DearPyGui bundled

**Negative**

- DearPyGui API breaks between minor versions — version is strictly pinned
- Styling and animations are limited compared to Qt (see [ADR-001](001-migrate-to-pyqt6.md))
- DPG widgets cannot be unit-tested headlessly; UI logic is integration-tested via mock mode only
- Windows-only viewport features (`ctypes.windll`, full-screen drawlist)

**Deferred**

- PyQt6/PySide6 migration evaluated in [ADR-001](001-migrate-to-pyqt6.md) (Proposed, pending spike)

## Related

- [architecture.md](../architecture.md) — UI layer in dependency diagram
- `wiibble/ui/ui.py`, `wiibble/ui/input.py`, `wiibble/ui/theme.py`
- `wiibble/session.py` — render loop
