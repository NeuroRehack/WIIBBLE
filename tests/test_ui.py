# tests/test_ui.py
from wiibble.ui.ui import dashed_line_segments


class TestDashedLineSegments:
    def test_zero_length_returns_empty(self):
        assert dashed_line_segments((5, 5), (5, 5)) == []

    def test_horizontal_line_segments(self):
        segments = dashed_line_segments((0, 0), (30, 0), dash=8, gap=6)
        assert len(segments) == 3
        assert segments[0] == ((0, 0), (8, 0))
        assert segments[1] == ((14, 0), (22, 0))
        assert segments[2] == ((28, 0), (30, 0))

    def test_vertical_line_endpoints(self):
        segments = dashed_line_segments((10, 0), (10, 20), dash=10, gap=5)
        assert segments[0][0] == (10, 0)
        assert segments[-1][1] == (10, 20)
