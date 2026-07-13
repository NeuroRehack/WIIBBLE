# THRIVE MQTT bridge

Companion process that publishes live WIIBBLE balance-board data to a THRIVE hub over MQTT.

## Enable in WIIBBLE

1. Open **Settings** → **THRIVE export**
2. Enable **Export to THRIVE hub**
3. Set **Broker host** to the THRIVE PC LAN IP (not `localhost` unless the hub runs on the same machine)
4. Set **Hub ID** to match `HUB_ID` in the THRIVE `.env` (default `demo`)

## Development

```bash
uv sync --extra thrive
# Terminal 1 — companion
uv run python -m wiibble.thrive --broker-host localhost --hub-id demo
# Terminal 2 — WIIBBLE with export enabled in settings
uv run python -m wiibble --mock --mock-scenario sway
```

## Packaging

Built as `WIIBBLE-THRIVE.exe` in `thrive/` next to `WIIBBLE.exe` via `compiler_thrive_companion.bat`.

See [docs/dev/THRIVE_BRIDGE.md](../../../docs/dev/THRIVE_BRIDGE.md) for clinical setup and troubleshooting.
