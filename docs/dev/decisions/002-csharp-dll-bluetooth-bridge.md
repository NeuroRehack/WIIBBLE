# ADR-002: C# DLL + pythonnet Bridge for Bluetooth Handshake

**Date:** 2026-07-06
**Status:** Accepted

## Context

The Nintendo Wii Balance Board does not expose standard Bluetooth HID data until Windows completes a vendor-specific pairing handshake. WIIBBLE must run on clinical Windows PCs as a single `.exe` without requiring clinicians to install Python or development tools.

An existing C# library (`WiiBalanceBoardLibrary`, derived from the WiiBalanceWalker project) already implemented the handshake correctly. Rewriting this logic in Python would duplicate fragile Windows Bluetooth behaviour and require ongoing maintenance against OS changes.

The main application is written in Python and compiled with Nuitka. A bridge is needed so Python can invoke the handshake once at startup, then hand off all streaming data to `hidapi`.

## Decision

Keep the C# `WiiBalanceBoardLibrary` DLL and load it at runtime via **pythonnet** (`clr.AddReference`). `wiibble/board/board_connection.py` calls `Connect()` once during session startup, then disconnects. All subsequent sensor reads use `hidapi` on the opened HID device.

## Consequences

**Positive**

- Reuses battle-tested handshake code; no rewrite risk for the hardest platform-specific step
- Handshake is isolated to startup — the render loop never touches .NET
- `hidapi` remains the only path for high-frequency 32-byte report reads (~100 Hz)

**Negative**

- Build requires .NET Framework 4.8 SDK and a separate `dotnet build` step
- `pythonnet` pins Python to 3.11–3.12 (3.13+ incompatible at time of writing)
- Two runtimes on the machine (.NET Framework + compiled Python) increase deployment surface

**Deferred**

- Consolidating C# interop into a dedicated `hardware_interface.py` module (see [TODO.md](../TODO.md))

## Related

- [architecture.md](../architecture.md) — board connection boundary
- `wiibble/board/board_connection.py`
- `WiiBalanceBoardLibrary/`
