# WIIBBLE — Open Issues & Roadmap

This file tracks open work. Completed items have been moved to [CHANGELOG.md](../CHANGELOG.md).  
For major architectural proposals see [Docs/decisions/](decisions/).

---

## 🔴 Bugs

### Installation
- [ ] `dotnet build` emits warning CS8618: *Non-nullable event 'BalanceBoardDataReceived' must contain a non-null value when exiting constructor. Consider declaring the event as nullable.*

---

## 🟡 Code Quality

- [ ] Further refactor `app.py` (e.g. extract `session.py`) for remaining logic
- [ ] Move C# interop code from `board_connection.py` into a dedicated `hardware_interface.py`
- [ ] Add `utils.py` for shared helper functions that don't fit elsewhere

---

## 🟢 Features & Improvements

- [ ] **Manual board recalibration** — add option to adjust `SCALE_FACTOR` based on known weights, to compensate for variation between boards and over time.
- [ ] Organise assets into subfolders (`assets/fonts/`, `assets/images/`)

---

## 🏗️ Phase 2 — Framework Migration

Migrate UI from DearPyGui to PyQt6/PySide6 for richer styling, smooth panel animations, and headless widget testing with `pytest-qt`.

**This is a significant architectural decision.** See the full proposal, spike requirements, and consequence analysis in:

> [Docs/decisions/0001-migrate-to-pyqt6.md](decisions/0001-migrate-to-pyqt6.md)

Status: **Proposed** — pending prototype spike.

---

## 🟢 CI Gaps

- [ ] Add workflow to build the C# DLL (`dotnet build`) on push
- [ ] Add workflow to build the Nuitka executable and archive as a CI artifact
