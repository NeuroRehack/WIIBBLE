"""Build the THRIVE node announce payload (schema parity with thrive-sim-wiibble)."""

from __future__ import annotations

from typing import Any

from wiibble.thrive.config import DEFAULT_NODE_ID, PUBLISH_RATE_HZ

COP_X_RANGE = (-216, 216)
COP_Y_RANGE = (-114, 114)
TOTAL_WT_RANGE = (0, 150)
QUAD_KG_RANGE = (0, 75)

RATE_HZ = PUBLISH_RATE_HZ


def build_announce(
    firmware: str,
    *,
    node_id: str = DEFAULT_NODE_ID,
    label: str = "WIIBBLE",
) -> dict[str, Any]:
    """Return the retained announce dict for MQTT publish."""
    return {
        "node_id": node_id,
        "node_class": "sensor",
        "node_type": "balance_board",
        "label": label,
        "firmware": firmware,
        "schema_version": "1",
        "channels": [
            {
                "name": "cop_x_mm",
                "label": "CoP X",
                "unit": "mm",
                "type": "scalar",
                "range": list(COP_X_RANGE),
                "rate_hz": RATE_HZ,
                "group": "cop",
                "group_axis": "x",
            },
            {
                "name": "cop_y_mm",
                "label": "CoP Y",
                "unit": "mm",
                "type": "scalar",
                "range": list(COP_Y_RANGE),
                "rate_hz": RATE_HZ,
                "group": "cop",
                "group_axis": "y",
            },
            {
                "name": "total_weight_kg",
                "label": "Total weight",
                "unit": "kg",
                "type": "scalar",
                "range": list(TOTAL_WT_RANGE),
                "rate_hz": RATE_HZ,
            },
            {
                "name": "quadrant_kg",
                "label": "Quadrant loads",
                "unit": "kg",
                "type": "quadrant",
                "range": list(QUAD_KG_RANGE),
                "rate_hz": RATE_HZ,
            },
        ],
        "signals_offered": [
            {
                "signal_type": "vector2",
                "label": "Centre of pressure",
                "channels": {"x": "cop_x_mm", "y": "cop_y_mm"},
            },
            {
                "signal_type": "scalar",
                "label": "Total weight",
                "channels": {"value": "total_weight_kg"},
            },
            {
                "signal_type": "quadrant",
                "label": "Quadrant loads",
                "channels": {"value": "quadrant_kg"},
            },
        ],
        "commands": [
            {
                "name": "tare",
                "label": "Tare / zero CoP",
                "description": (
                    "Sets the current centre-of-pressure position "
                    "as the new zero reference."
                ),
                "params": [],
            }
        ],
        "settings": [
            {
                "name": "smoothing_window",
                "label": "Smoothing window",
                "type": "integer",
                "min": 1,
                "max": 20,
                "default": 5,
                "unit": "samples",
                "persist": True,
            },
            {
                "name": "board_orientation",
                "label": "Board orientation",
                "type": "enum",
                "options": [
                    {"value": "standard", "label": "Standard"},
                    {"value": "rotated-180", "label": "Rotated 180"},
                ],
                "default": "standard",
                "persist": True,
            },
        ],
    }
