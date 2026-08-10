"""Unit tests for cursor_geometry pure helpers."""

from __future__ import annotations

import pytest

from wiibble.ui.cursor_geometry import (
    avatar_draw_size,
    logical_rect_to_viewport_bounds,
    pick_rect_edge,
    radius_from_center,
    screen_cursor_radius,
    trail_size_fraction,
    trail_stamp_alpha,
)
from wiibble.utils.constants import TARGET_MIN_LOGICAL_SPAN
from wiibble.utils.state import Settings


def _settings(**kwargs: object) -> Settings:
    """Return Settings with optional overrides."""
    s = Settings()
    for key, value in kwargs.items():
        setattr(s, key, value)
    return s


class TestScreenCursorRadius:
    def test_uses_cursor_size(self) -> None:
        assert screen_cursor_radius(_settings(cursor_size=25)) == 25

    def test_minimum_one(self) -> None:
        assert screen_cursor_radius(_settings(cursor_size=0)) == 1


class TestAvatarDrawSize:
    def test_preserves_aspect_ratio(self) -> None:
        w, h = avatar_draw_size(_settings(cursor_size=20), 100, 200)
        assert h == 40  # 2 * radius
        assert w == 20  # half aspect

    def test_minimum_width_one(self) -> None:
        w, _ = avatar_draw_size(_settings(cursor_size=1), 1, 10000)
        assert w >= 1


class TestRadiusFromCenter:
    def test_distance_from_center(self) -> None:
        r = radius_from_center(3.0, 4.0, 0.0, 0.0)
        assert r == pytest.approx(5.0)

    def test_clamps_to_minimum(self) -> None:
        min_r = TARGET_MIN_LOGICAL_SPAN / 2.0
        r = radius_from_center(0.0, 0.0, 0.0, 0.0)
        assert r == min_r


class TestLogicalRectToViewportBounds:
    def test_orders_corners(self) -> None:
        min_vx, min_vy, max_vx, max_vy = logical_rect_to_viewport_bounds(
            (1.0, 2.0),
            (-1.0, -2.0),
            cx=100.0,
            cy=100.0,
            zoom=1.0,
            flip_horizontal=False,
            flip_vertical=False,
        )
        assert min_vx <= max_vx
        assert min_vy <= max_vy


class TestPickRectEdge:
    def test_picks_nearest_edge(self) -> None:
        target = {"min": (-5.0, -5.0), "max": (5.0, 5.0)}
        settings = _settings(zoom_factor=10.0)
        edge = pick_rect_edge(100.0, 100.0, target, 100.0, 100.0, settings)
        assert edge in {"left", "right", "top", "bottom"}


class TestTrailHelpers:
    def test_trail_size_fraction(self) -> None:
        assert trail_size_fraction(5, 10) == pytest.approx(0.5)

    def test_trail_stamp_alpha_fixed(self) -> None:
        assert trail_stamp_alpha(0.3) == 200
