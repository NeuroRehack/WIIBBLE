# tests/test_data_processing.py
# Unit tests for the pure pipeline functions in data_processing.py.
# No hardware, no DearPyGui — all inputs are constructed in-process.
import pytest

from wiibble.features.data_processing import (
    apply_filter,
    calculate_coordinates,
    calculate_force_deviation_kg,
    parse_data,
    read_latest_data,
)
from wiibble.utils.constants import COORD_SCALE, SCALE_FACTOR

# ---------------------------------------------------------------------------
# read_latest_data
# ---------------------------------------------------------------------------


class _QueueDevice:
    """Test double that returns queued read() results in order."""

    def __init__(self, responses):
        self._responses = list(responses)

    def read(self, size):
        if self._responses:
            return self._responses.pop(0)
        return []


class TestReadLatestData:
    def test_empty_buffer_returns_none(self):
        device = _QueueDevice([[], []])
        data, drained = read_latest_data(device)
        assert data is None
        assert drained == 0

    def test_single_report(self):
        report = [0] * 32
        device = _QueueDevice([report])
        data, drained = read_latest_data(device)
        assert data == report
        assert drained == 1

    def test_drains_queue_and_returns_last(self):
        r1, r2, r3 = [1] * 32, [2] * 32, [3] * 32
        device = _QueueDevice([r1, r2, r3, []])
        data, drained = read_latest_data(device)
        assert data == r3
        assert drained == 3

    def test_stops_at_first_empty_after_reports(self):
        r1, r2 = [1] * 32, [2] * 32
        device = _QueueDevice([r1, [], r2])
        data, drained = read_latest_data(device)
        assert data == r1
        assert drained == 1

    def test_read_error_returns_partial_latest(self):
        class ErrDevice:
            def __init__(self):
                self._n = 0

            def read(self, size):
                self._n += 1
                if self._n == 1:
                    return [5] * 32
                raise OSError("disconnected")

        data, drained = read_latest_data(ErrDevice())
        assert data == [5] * 32
        assert drained == 1


# ---------------------------------------------------------------------------
# parse_data
# ---------------------------------------------------------------------------


class TestParseData:
    def test_all_zero_bytes_returns_zero_corners(self, data_struct, zero_data):
        result = parse_data(zero_data, data_struct)
        assert result == {
            "top_right": 0.0,
            "bottom_right": 0.0,
            "top_left": 0.0,
            "bottom_left": 0.0,
        }

    def test_single_corner_known_bytes(self, data_struct, zero_data):
        # Set top_right bytes (rawIndex=3): integer=100, fractional=128
        zero_data[3] = 100
        zero_data[4] = 128
        result = parse_data(zero_data, data_struct)
        expected = round((100 + 128 / 255) * SCALE_FACTOR, 2)
        assert result["top_right"] == expected

    def test_all_four_corners_independently(self, data_struct, zero_data):
        # Each corner gets distinct values
        zero_data[3], zero_data[4] = 10, 0  # top_right
        zero_data[5], zero_data[6] = 20, 0  # bottom_right
        zero_data[7], zero_data[8] = 30, 0  # top_left
        zero_data[9], zero_data[10] = 40, 0  # bottom_left
        result = parse_data(zero_data, data_struct)
        assert result["top_right"] == round(10 * SCALE_FACTOR, 2)
        assert result["bottom_right"] == round(20 * SCALE_FACTOR, 2)
        assert result["top_left"] == round(30 * SCALE_FACTOR, 2)
        assert result["bottom_left"] == round(40 * SCALE_FACTOR, 2)

    def test_tare_offset_is_subtracted(self, data_struct, zero_data):
        # top_right: rawIndex=3, integer byte=100, tare=50
        zero_data[3] = 100
        data_struct["top_right"]["tare"] = 50
        result = parse_data(zero_data, data_struct)
        expected = round((100 - 50) * SCALE_FACTOR, 2)
        assert result["top_right"] == expected

    def test_max_byte_values(self, data_struct, zero_data):
        # data[3]=255, data[4]=255 → (255 + 255/255) * SCALE_FACTOR = 256 * SCALE_FACTOR
        zero_data[3] = 255
        zero_data[4] = 255
        result = parse_data(zero_data, data_struct)
        expected = round((255 + 255 / 255) * SCALE_FACTOR, 2)
        assert result["top_right"] == expected

    def test_fractional_byte_contributes_fractional_kg(self, data_struct, zero_data):
        # Integer part zero, only fractional — should yield a small positive value
        zero_data[3] = 0
        zero_data[4] = 255
        result = parse_data(zero_data, data_struct)
        expected = round((0 + 255 / 255) * SCALE_FACTOR, 2)
        assert result["top_right"] == expected
        assert result["top_right"] > 0


# ---------------------------------------------------------------------------
# apply_filter
# ---------------------------------------------------------------------------


class TestApplyFilter:
    def _corners(self, val: float) -> dict:
        return {
            "top_right": val,
            "bottom_right": val,
            "top_left": val,
            "bottom_left": val,
        }

    def test_window_one_is_passthrough(self):
        buf = []
        corners = self._corners(9.0)
        result = apply_filter(corners, buf, filter_window=1)
        assert result == corners

    def test_window_one_buffer_stays_at_one(self):
        buf = []
        for _ in range(5):
            apply_filter(self._corners(5.0), buf, filter_window=1)
        assert len(buf) == 1

    def test_window_two_two_identical_frames(self):
        buf = []
        c = self._corners(9.0)
        apply_filter(c, buf, filter_window=2)
        result = apply_filter(c, buf, filter_window=2)
        for v in result.values():
            assert v == pytest.approx(9.0)

    def test_window_two_two_different_frames(self):
        buf = []
        c1 = self._corners(10.0)
        c2 = self._corners(20.0)
        apply_filter(c1, buf, filter_window=2)
        result = apply_filter(c2, buf, filter_window=2)
        for v in result.values():
            assert v == pytest.approx(15.0)

    def test_partial_window_averages_available_frames_only(self):
        # window=5 with only 3 frames: average of 10, 20, 30 = 20
        buf = []
        for val in [10.0, 20.0, 30.0]:
            result = apply_filter(self._corners(val), buf, filter_window=5)
        for v in result.values():
            assert v == pytest.approx(20.0)

    def test_buffer_does_not_exceed_window_size(self):
        buf = []
        for i in range(10):
            apply_filter(self._corners(float(i)), buf, filter_window=3)
        assert len(buf) == 3

    def test_oldest_frame_dropped_when_full(self):
        buf = []
        # Feed frames: 0, 0, 0, 30 with window=3
        # After frame 4 the buffer should hold [0, 0, 30] → average = 10
        for _ in range(3):
            apply_filter(self._corners(0.0), buf, filter_window=3)
        result = apply_filter(self._corners(30.0), buf, filter_window=3)
        for v in result.values():
            assert v == pytest.approx(10.0)


# ---------------------------------------------------------------------------
# calculate_force_deviation_kg
# ---------------------------------------------------------------------------


class TestCalculateForceDeviationKg:
    def test_balanced_gives_zero(self):
        assert calculate_force_deviation_kg(9, 9, 9, 9) == (0, 0)

    def test_all_weight_on_right_gives_positive_x(self):
        x, y = calculate_force_deviation_kg(0, 20, 0, 20)
        assert x == pytest.approx(40.0)
        assert y == pytest.approx(0.0)

    def test_all_weight_on_left_gives_negative_x(self):
        x, y = calculate_force_deviation_kg(20, 0, 20, 0)
        assert x == pytest.approx(-40.0)
        assert y == pytest.approx(0.0)

    def test_all_weight_forward_gives_positive_y(self):
        x, y = calculate_force_deviation_kg(20, 20, 0, 0)
        assert x == pytest.approx(0.0)
        assert y == pytest.approx(40.0)

    def test_all_weight_back_gives_negative_y(self):
        x, y = calculate_force_deviation_kg(0, 0, 20, 20)
        assert x == pytest.approx(0.0)
        assert y == pytest.approx(-40.0)

    def test_asymmetric_diagonal(self):
        # tl=10, tr=5, bl=3, br=2
        # x = (5+2) - (10+3) = 7 - 13 = -6
        # y = (10+5) - (3+2)  = 15 - 5 = 10
        x, y = calculate_force_deviation_kg(10, 5, 3, 2)
        assert x == pytest.approx(-6.0)
        assert y == pytest.approx(10.0)

    def test_negative_values_tare_artifacts(self):
        # Negative values can occur after tare overcorrection
        x, y = calculate_force_deviation_kg(-5, 5, -5, 5)
        assert x == pytest.approx(20.0)
        assert y == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# calculate_coordinates
# ---------------------------------------------------------------------------


class TestCalculateCoordinates:
    SW = 1280.0
    SH = 720.0

    def test_zero_weight_returns_origin(self):
        # Must not raise ZeroDivisionError
        result = calculate_coordinates(
            9, 9, 9, 9, weight=0, screen_width=self.SW, screen_height=self.SH
        )
        assert result == (0.0, 0.0)

    def test_balanced_corners_returns_origin(self):
        x, y = calculate_coordinates(
            9, 9, 9, 9, weight=36, screen_width=self.SW, screen_height=self.SH
        )
        assert x == pytest.approx(0.0, abs=1e-9)
        assert y == pytest.approx(0.0, abs=1e-9)

    def test_zoom_doubles_output(self):
        tl, tr, bl, br = 10, 5, 5, 10
        w = tl + tr + bl + br
        x1, y1 = calculate_coordinates(
            tl, tr, bl, br, weight=w, screen_width=self.SW, screen_height=self.SH, zoom=1.0
        )
        x2, y2 = calculate_coordinates(
            tl, tr, bl, br, weight=w, screen_width=self.SW, screen_height=self.SH, zoom=2.0
        )
        assert x2 == pytest.approx(2 * x1)
        assert y2 == pytest.approx(2 * y1)

    def test_double_screen_width_doubles_x(self):
        tl, tr, bl, br = 10, 5, 5, 10
        w = tl + tr + bl + br
        x1, _ = calculate_coordinates(
            tl, tr, bl, br, weight=w, screen_width=self.SW, screen_height=self.SH
        )
        x2, _ = calculate_coordinates(
            tl, tr, bl, br, weight=w, screen_width=self.SW * 2, screen_height=self.SH
        )
        assert x2 == pytest.approx(2 * x1)

    def test_right_lean_gives_positive_x(self):
        # More weight on right: tr+br > tl+bl
        x, _ = calculate_coordinates(
            0, 18, 0, 18, weight=36, screen_width=self.SW, screen_height=self.SH
        )
        assert x > 0

    def test_left_lean_gives_negative_x(self):
        x, _ = calculate_coordinates(
            18, 0, 18, 0, weight=36, screen_width=self.SW, screen_height=self.SH
        )
        assert x < 0

    def test_backward_lean_gives_positive_y(self):
        # More weight on bottom: bl+br > tl+tr
        _, y = calculate_coordinates(
            0, 0, 18, 18, weight=36, screen_width=self.SW, screen_height=self.SH
        )
        assert y > 0

    def test_forward_lean_gives_negative_y(self):
        # More weight on top: tl+tr > bl+br
        _, y = calculate_coordinates(
            18, 18, 0, 0, weight=36, screen_width=self.SW, screen_height=self.SH
        )
        assert y < 0

    def test_coord_scale_applied(self):
        # With balanced corners one axis and unbalanced other, the amplitude
        # should be proportional to COORD_SCALE * screen_dim / weight
        # All weight on right: tl=0, tr=w, bl=0, br=w → x = 0.5 * SW * COORD_SCALE
        w = 72.0
        x, _ = calculate_coordinates(
            0, w / 2, 0, w / 2, weight=w, screen_width=self.SW, screen_height=self.SH
        )
        assert x == pytest.approx(0.5 * self.SW * COORD_SCALE)
