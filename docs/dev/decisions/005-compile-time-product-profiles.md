# ADR-005: Compile-Time Product Profiles

**Date:** 2026-08-14
**Status:** Accepted

## Context

WIIBBLE ships as a single Windows `.exe` plus optional companion processes for THRIVE MQTT export and in-app HTML session reports. Some deployments need the live CoP tool without those two in-app features: they must not appear in Settings, and their companions must not be compiled or installed.

Runtime toggles (`thrive_enabled`, `auto_report_after_recording`) cannot meet that bar. The glue code would still import into the main binary, the settings widgets would still render, and `compiler.bat` would still build `WIIBBLE-THRIVE.exe` and `WIIBBLE-SessionReport.exe`.

Forking a second git branch would diverge from the clinical full product. Splitting Thrive or reports into separate installable packages is more machinery than two optional companions need.

Offline analysis CLIs (`wiibble-report`, `wiibble-process-recordings`) stay available in development regardless of the Windows installer flavor.

## Decision

Keep one codebase and version. Select in-app Thrive and session reports at **Nuitka build time** via `WIIBBLE_PROFILE` (`full` default, `lite` both off) and optional `WIIBBLE_FEATURE_THRIVE` / `WIIBBLE_FEATURE_SESSION_REPORT` overrides.

Committed [`src/wiibble/product.py`](../../src/wiibble/product.py) defaults both flags to True. The compiler writes a gitignored overlay (`_product_build.py`) with False literals when a feature is off, then deletes the overlay after Nuitka so the working tree is not left on a lite configuration. Call sites read `wiibble.product.FEATURE_*` and skip imports, settings widgets, and companion `.bat` builds. When session reports are off, Nuitka also gets `--nofollow-import-to=wiibble.session_report`.

Full builds keep the existing installer name `WIIBBLE-{version}-Setup.exe`. Lite (and mixed) builds append a flavor suffix (`-lite`, `-no-thrive`, `-no-reports`). CI/release stays on the full profile unless `WIIBBLE_PROFILE` is set.

Leftover keys in `%APPDATA%\WIIBBLE\settings.json` are ignored in memory for compiled-out features and are not rewritten.

## Consequences

**Positive**

- One repo and version line; full `compiler.bat` with no env vars matches today's recipe
- Lite installers omit companion folders and hide the corresponding Settings sections
- Overlay generation avoids rewriting committed `product.py` (a lite compile cannot silently poison the next full compile)

**Negative**

- Two Nuitka recipes to smoke-test after compiler changes
- Nuitka still follows import statements unless they are conditional **and** `--nofollow-import-to` matches; leftover module-level imports can keep glue in a lite main exe

**Deferred**

- Shipping both full and lite artifacts from the same CI release job
- Installer component checkboxes (would omit files at install time without excluding them from the compiled main exe)

## Related

- [ADR-003](003-session-report-companion.md) — session-report companion (full profile only)
- [THRIVE_BRIDGE.md](../THRIVE_BRIDGE.md) — Thrive companion (full profile only)
- [`compiler.bat`](../../../compiler.bat), [`scripts/write_product_overlay.py`](../../../scripts/write_product_overlay.py)
