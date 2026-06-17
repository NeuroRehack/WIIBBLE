# tests/test_mock_board.py
"""Tests for MockHIDDevice calibration phase behaviour."""

import time

from wiibble.board.mock_board import MockHIDDevice
from wiibble.features.data_processing import measure_weight

_DEFAULT_DATA_STRUCT = {
    "top_right": {"rawIndex": 3, "tare": 0},
    "bottom_right": {"rawIndex": 5, "tare": 0},
    "top_left": {"rawIndex": 7, "tare": 0},
    "bottom_left": {"rawIndex": 9, "tare": 0},
}


class TestMockCalibrationPhases:
    def test_step_on_stable_persists_until_enter_running_mode(self):
        """step_on_stable must not time out before sensitivity_calibration finishes."""
        device = MockHIDDevice("calibration")
        device.open(0, 0)
        device.trigger_step_on()
        assert device._phase == "step_on_stable"

        time.sleep(4)
        assert device._phase == "step_on_stable"

        device.enter_running_mode()
        assert device._phase == "normal"

    def test_blocking_reads_required_for_stable_calibration_weight(self):
        """Blocking mode yields a full ~72 kg reading during step_on_stable."""
        device = MockHIDDevice("calibration")
        device.open(0, 0)
        device.trigger_step_on()

        device.set_nonblocking(0)
        weight = measure_weight(device, _DEFAULT_DATA_STRUCT)
        assert 60.0 < weight < 80.0
