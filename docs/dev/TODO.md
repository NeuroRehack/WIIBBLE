# WIIBBLE — Open Issues & Roadmap

This file tracks open work. Completed items have been moved to [CHANGELOG.md](../CHANGELOG.md).  
For major architectural proposals see [decisions/](decisions/).

---

## 🔴 Bugs

### Installation
- [ ] `dotnet build` emits warning CS8618: *Non-nullable event 'BalanceBoardDataReceived' must contain a non-null value when exiting constructor. Consider declaring the event as nullable.*

---

## 🟡 Code Quality

- [ ] Further refactor `wiibble/app.py` (e.g. extract `wiibble/session.py`) for remaining logic
- [ ] Move C# interop code from `wiibble/board/board_connection.py` into a dedicated `wiibble/board/hardware_interface.py`
- [ ] Add `utils.py` for shared helper functions that don't fit elsewhere

---

## 🟢 Features & Improvements

- [x] **Manual board recalibration** — `scale_factor` in settings, calibrated from a known reference mass via **Cal scale**.
- [ ] Organise assets into subfolders (`assets/fonts/`, `assets/images/`)

---

## 🏗️ Phase 2 — Framework Migration

Migrate UI from DearPyGui to PyQt6/PySide6 for richer styling, smooth panel animations, and headless widget testing with `pytest-qt`.

**This is a significant architectural decision.** See the full proposal, spike requirements, and consequence analysis in:

> [decisions/001-migrate-to-pyqt6.md](decisions/001-migrate-to-pyqt6.md)

Status: **Proposed** — pending prototype spike.

---

## 🟢 CI Gaps

- [ ] Add workflow to build the C# DLL (`dotnet build`) on push
- [ ] Add workflow to build the Nuitka executable and archive as a CI artifact
