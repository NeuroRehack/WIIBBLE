# ADR-003: Companion Executable for Session Reports

**Date:** 2026-07-06
**Status:** Accepted

## Context

Clinicians need an interactive HTML posturographic report immediately after each recording so they can review sway metrics with the patient at the bedside. The analysis pipeline depends on scipy (Butterworth filtering, SWARII resampling) and plotly/jinja2 for HTML generation — roughly tens of megabytes of dependencies.

The main WIIBBLE binary is built with Nuitka for fast startup and minimal antivirus friction on hospital PCs. Bundling scipy and plotly into the main `.exe` would significantly increase build time, binary size, and startup cost for a feature used only at the end of a recording.

Blocking the render loop during analysis (~2–4 s for a 30 s recording) would also freeze the live CoP display.

## Decision

Ship a separate **companion executable** (`WIIBBLE-SessionReport.exe`, built by `compiler_session_report.bat`) installed in a `session_report/` subfolder next to `WIIBBLE.exe`.

When `settings.auto_report_after_recording` is enabled (default), `wiibble/session.py` calls `launch_session_report_async()` after `_save_recording_csv()` returns. The companion runs `run_session_report()` — feature extraction (if duration ≥ 20 s) plus HTML generation — and optionally opens the report in the default browser. The main app polls a progress file and shows toast/status updates without blocking the sensor loop.

In development, the launcher falls back to `python -m wiibble.cli.session_report`.

Offline batch tools (`wiibble-process-recordings`, `wiibble-report`) remain available for retrospective analysis.

## Consequences

**Positive**

- Main `.exe` stays lean — no scipy/plotly in the hot path
- Report generation does not block real-time CoP rendering
- Same analysis code path in companion, dev module, and offline CLIs
- Clinicians get immediate feedback with progress UI in the settings panel

**Negative**

- Two binaries to build, version, and install (main app + companion)
- Installer must place companion in the correct relative path
- Dev environments need `uv sync --extra analysis` for the fallback module

**Deferred**

- None — companion is the permanent architecture for in-session reports

## Related

- [DATA_PIPELINE.md](../DATA_PIPELINE.md) §7b — in-session report flow
- `wiibble/session_report/launcher.py`, `runner.py`
- `compiler_session_report.bat`
