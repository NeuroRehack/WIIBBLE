"""Tests for WIIBBLE → THRIVE channel transforms."""

from wiibble.thrive.transform import (
    board_orientation_from_flips,
    flips_from_board_orientation,
    frame_to_channels,
)
from wiibble.utils.constants import WBB_SENSOR_DIST_AP_CM, WBB_SENSOR_DIST_ML_CM


def test_frame_to_channels_balanced_weight_centred_cop():
    """Equal corner loads → zero CoP."""
    channels = frame_to_channels(17.0, 17.0, 17.0, 17.0)
    assert channels["cop_x_mm"] == 0.0
    assert channels["cop_y_mm"] == 0.0
    assert channels["total_weight_kg"] == 68.0
    assert channels["quadrant_kg"] == {
        "tl": 17.0,
        "tr": 17.0,
        "bl": 17.0,
        "br": 17.0,
    }


def test_frame_to_channels_lean_right():
    """More weight on right → positive CoP X (mediolateral)."""
    channels = frame_to_channels(10.0, 30.0, 10.0, 30.0)
    total = 80.0
    x_kg = (30 + 30) - (10 + 10)  # 40
    expected_x = WBB_SENSOR_DIST_ML_CM * 10 * x_kg / total
    assert channels["cop_x_mm"] == round(expected_x, 2)
    assert channels["cop_y_mm"] == 0.0


def test_frame_to_channels_lean_forward():
    """More weight on front (top) → positive CoP Y (anteroposterior)."""
    channels = frame_to_channels(25.0, 25.0, 15.0, 15.0)
    total = 80.0
    y_kg = (25 + 25) - (15 + 15)  # 20
    expected_y = WBB_SENSOR_DIST_AP_CM * 10 * y_kg / total
    assert channels["cop_x_mm"] == 0.0
    assert channels["cop_y_mm"] == round(expected_y, 2)


def test_frame_to_channels_tare_offset_zeros_cop():
    """Applying cop offset after measuring current position zeros CoP."""
    channels = frame_to_channels(10.0, 30.0, 10.0, 30.0)
    from wiibble.thrive.transform import cop_offset_from_channels

    ox, oy = cop_offset_from_channels(channels)
    tared = frame_to_channels(
        10.0, 30.0, 10.0, 30.0, cop_offset_x_kg=ox, cop_offset_y_kg=oy
    )
    assert tared["cop_x_mm"] == 0.0
    assert tared["cop_y_mm"] == 0.0


def test_board_orientation_mapping():
    assert board_orientation_from_flips(False, False) == "standard"
    assert board_orientation_from_flips(True, True) == "rotated-180"
    assert flips_from_board_orientation("rotated-180") == (True, True)
    assert flips_from_board_orientation("standard") == (False, False)


def test_rotated_180_negates_cop():
    base = frame_to_channels(10.0, 30.0, 10.0, 30.0)
    rotated = frame_to_channels(
        10.0, 30.0, 10.0, 30.0, board_orientation="rotated-180"
    )
    assert rotated["cop_x_mm"] == -base["cop_x_mm"]
    assert rotated["cop_y_mm"] == -base["cop_y_mm"]


def test_cop_offset_zero_weight_returns_zeros():
    from wiibble.thrive.transform import cop_offset_from_channels

    assert cop_offset_from_channels({"total_weight_kg": 0.0}) == (0.0, 0.0)
