# THRIVE MQTT bridge

WIIBBLE can publish live balance-board data to a [THRIVE](https://github.com/NeuroRehack/THRIVE) rehabilitation hub while a session is running. This replaces the Python `thrive-sim-wiibble` simulator when real hardware is available.

## Clinical setup

1. **THRIVE hub** — on the demo/hospital PC, start the hub (`just up` in the THRIVE repo). Note the PC’s LAN IP and confirm `HUB_ID` in `.env` (default `demo`).
2. **Network** — the Windows WIIBBLE PC must reach the hub on **TCP 1883** (MQTT). Allow this through the hospital firewall if needed.
3. **WIIBBLE** — Settings → **THRIVE export**:
   - Enable **Export to THRIVE hub**
   - **Broker host** — LAN IP of the THRIVE PC (not `localhost` unless the hub is on the same machine)
   - **Hub ID** — must match THRIVE `HUB_ID` (default `demo`)
4. **Pair board** and start WIIBBLE as usual. The companion process (`WIIBBLE-THRIVE.exe` or `python -m wiibble.thrive` in dev) starts when the live session begins.
5. **THRIVE UI** — open `http://<hub-ip>:8080`, confirm device **WIIBBLE** is online, add **CoP Plot**, **Quadrant Load**, and **Balance Cursor**, then **Start Session**.

Do **not** run `just sim-wiibble` at the same time — node id `wiibble_01` is distinct from `wiibble_sim_01`, but running both can confuse operators.

## Architecture

```
WIIBBLE.exe (HID ~100 Hz)
    → session hook (UDP frames, non-blocking)
    → WIIBBLE-THRIVE.exe / python -m wiibble.thrive
    → Mosquitto (thrive/{HUB_ID}/nodes/wiibble_01/...)
    → THRIVE hub UI
```

Bidirectional IPC on localhost UDP:

| Port | Direction | Purpose |
|------|-----------|---------|
| 47681 | main → companion | Smoothed corner kg frames |
| 47682 | companion → main | `tare` command, settings sync |

See [003-session-report-companion.md](decisions/003-session-report-companion.md) for the companion packaging pattern.

## MQTT contract

Authoritative THRIVE references:

- `THRIVE/src/thrive/sims/wiibble.py` — announce/data shape
- `THRIVE/docs/dev/architecture.md` — topic tree

Topics (for `HUB_ID=demo`, `node_id=wiibble_01`):

```
thrive/demo/nodes/wiibble_01/announce
thrive/demo/nodes/wiibble_01/status
thrive/demo/nodes/wiibble_01/data          @ ~50 Hz
thrive/demo/nodes/wiibble_01/settings
thrive/demo/nodes/wiibble_01/command       (subscribe)
thrive/demo/nodes/wiibble_01/settings/set  (subscribe)
thrive/demo/nodes/wiibble_01/command_response
```

## Field mapping (WIIBBLE → THRIVE)

| THRIVE channel | Source in WIIBBLE |
|----------------|-------------------|
| `cop_x_mm` | Leach CoP ML from smoothed corners × 10 (mm) |
| `cop_y_mm` | Leach CoP AP from smoothed corners × 10 (mm) |
| `total_weight_kg` | Sum of smoothed corner kg |
| `quadrant_kg` | Actual corner kg (`tl/tr/bl/br`), not synthetic quadrants |

Pipeline: `parse_data` → `apply_filter` (display path) → `calculate_force_deviation_kg` → `apply_axis_flip` → CoP formula using **live** total weight.

**Settings mapping:**

| THRIVE setting | WIIBBLE setting |
|----------------|-----------------|
| `smoothing_window` | `filter_window` |
| `board_orientation` | `flip_horizontal` + `flip_vertical` both true → `rotated-180` (v1) |

**Tare:** hub `tare` command zeros CoP in the bridge and queues WIIBBLE hardware tare via `session_state["action"]`.

## Verification

```bash
# On THRIVE PC
mosquitto_sub -h localhost -t 'thrive/demo/nodes/wiibble_01/announce' -v
mosquitto_sub -h localhost -t 'thrive/demo/nodes/wiibble_01/data' -v
```

Expect retained announce, online status, and `data` at ~50 Hz while standing on the board.

## Troubleshooting

| Symptom | Check |
|---------|--------|
| Device not in hub UI | Broker host/IP, firewall port 1883, `HUB_ID` match, companion log |
| Device online, values stuck at 0.0 | `mosquitto_sub .../data` should show **~50 msg/s**; companion must run on **WIIBBLE PC**, not THRIVE hub |
| Device online, no viz | Session **Started** in hub; tiles use `signals/+/data` via signal mapper |
| Scalar Gauge empty | Map scalar input to **Total weight** in tile footer; restart session after node streams |
| Wrong CoP orientation | WIIBBLE flip toggles vs hub `board_orientation`; compare to WIIBBLE on-screen cursor |
| Stale tiles after quit | LWT/status offline — wait ~2 s; confirm companion exited |
| `just sim-wiibble` broken | Disable THRIVE export in WIIBBLE; sim uses `wiibble_sim_01` |

**Low MQTT rate** (one message every few seconds): enable THRIVE export in WIIBBLE settings, **restart the WIIBBLE session** (hook starts companion + 50 Hz UDP sender). Do not run `python -m wiibble.thrive` manually on the hub machine.

## Known POC deviations

- AP half-distance: WIIBBLE uses 11.9 cm (Leach 2014); THRIVE announce range uses ±114 mm. Minor mismatch; CoP is clamped to announce ranges.
- Hub `board_orientation` only maps full 180° rotation (both axis flips), not single-axis flips.
- Quadrants publish **measured** corner loads; THRIVE simulator derives synthetic quadrants from CoP — values differ but channel schema matches.

## Development

```bash
uv sync --extra thrive
uv run python -m wiibble.thrive --broker-host localhost --hub-id demo
# Enable export in WIIBBLE settings; run mock or real session
```

Build companion: `compiler_thrive_companion.bat` (also invoked from `compiler.bat`).

## Future

Bare-metal embedded node on board hardware with the same MQTT contract, replacing this Windows companion.
