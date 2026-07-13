"""Pure WIIBBLE frame → THRIVE channel transforms."""

from __future__ import annotations

from typing import Any

from wiibble.features.data_processing import (
    apply_axis_flip,
    calculate_force_deviation_kg,
)
from wiibble.thrive.announce import COP_X_RANGE, COP_Y_RANGE, QUAD_KG_RANGE, TOTAL_WT_RANGE
from wiibble.utils.constants import WBB_SENSOR_DIST_AP_CM, WBB_SENSOR_DIST_ML_CM


def board_orientation_from_flips(
    flip_horizontal: bool, flip_vertical: bool
) -> str:
    """Map WIIBBLE axis flips to THRIVE board_orientation (v1: 180° only)."""
    if flip_horizontal and flip_vertical:
        return "rotated-180"
    return "standard"


def flips_from_board_orientation(board_orientation: str) -> tuple[bool, bool]:
    """Map THRIVE board_orientation to WIIBBLE flip toggles (v1)."""
    if board_orientation == "rotated-180":
        return True, True
    return False, False


def frame_to_channels(
    top_left: float,
    top_right: float,
    bottom_left: float,
    bottom_right: float,
    *,
    flip_horizontal: bool = False,
    flip_vertical: bool = False,
    cop_offset_x_kg: float = 0.0,
    cop_offset_y_kg: float = 0.0,
    board_orientation: str = "standard",
) -> dict[str, Any]:
    """Convert smoothed corner kg values to THRIVE MQTT channel dict.

    Uses the display path: force deviation with axis flips, Leach CoP formula
    with live total weight, and actual corner loads for quadrants.
    """
    x_kg, y_kg = calculate_force_deviation_kg(
        top_left, top_right, bottom_left, bottom_right
    )
    x_kg, y_kg = apply_axis_flip(x_kg, y_kg, flip_horizontal, flip_vertical)
    x_kg -= cop_offset_x_kg
    y_kg -= cop_offset_y_kg

    total_kg = top_left + top_right + bottom_left + bottom_right
    total_kg = max(TOTAL_WT_RANGE[0], min(total_kg, TOTAL_WT_RANGE[1]))

    if total_kg > 0:
        cop_x_mm = WBB_SENSOR_DIST_ML_CM * 10.0 * x_kg / total_kg
        cop_y_mm = WBB_SENSOR_DIST_AP_CM * 10.0 * y_kg / total_kg
    else:
        cop_x_mm = 0.0
        cop_y_mm = 0.0

    if board_orientation == "rotated-180":
        cop_x_mm, cop_y_mm = -cop_x_mm, -cop_y_mm

    cop_x_mm = max(COP_X_RANGE[0], min(cop_x_mm, COP_X_RANGE[1]))
    cop_y_mm = max(COP_Y_RANGE[0], min(cop_y_mm, COP_Y_RANGE[1]))

    quad_max = QUAD_KG_RANGE[1]
    quadrant_kg = {
        "tl": round(max(0.0, min(top_left, quad_max)), 2),
        "tr": round(max(0.0, min(top_right, quad_max)), 2),
        "bl": round(max(0.0, min(bottom_left, quad_max)), 2),
        "br": round(max(0.0, min(bottom_right, quad_max)), 2),
    }

    return {
        "cop_x_mm": round(cop_x_mm, 2),
        "cop_y_mm": round(cop_y_mm, 2),
        "total_weight_kg": round(total_kg, 2),
        "quadrant_kg": quadrant_kg,
    }


def cop_offset_from_channels(channels: dict[str, Any]) -> tuple[float, float]:
    """Derive kg offsets that zero the current CoP (inverse of frame_to_channels)."""
    total_kg = float(channels.get("total_weight_kg", 0.0))
    if total_kg <= 0:
        return 0.0, 0.0
    cop_x_mm = float(channels.get("cop_x_mm", 0.0))
    cop_y_mm = float(channels.get("cop_y_mm", 0.0))
    x_kg = cop_x_mm * total_kg / (WBB_SENSOR_DIST_ML_CM * 10.0)
    y_kg = cop_y_mm * total_kg / (WBB_SENSOR_DIST_AP_CM * 10.0)
    return x_kg, y_kg
