"""Pure cursor and target geometry helpers (no Dear PyGui imports)."""

from __future__ import annotations

import math
from typing import Any

from wiibble.features.data_processing import logical_to_viewport
from wiibble.utils.constants import TARGET_EDGE_HIT_TOLERANCE, TARGET_MIN_LOGICAL_SPAN
from wiibble.utils.state import Settings

RectEdge = str


def screen_cursor_radius(settings: Settings) -> int:
    """Return cursor radius in viewport pixels (independent of canvas zoom).

    Args:
        settings: Application settings containing ``cursor_size``.

    Returns:
        Cursor radius in screen pixels, at least 1.
    """
    return max(1, int(settings.cursor_size))


def avatar_draw_size(
    settings: Settings, image_width: int, image_height: int
) -> tuple[int, int]:
    """Return avatar cursor width and height in screen pixels.

    Args:
        settings: Application settings containing ``cursor_size``.
        image_width: Person texture width in pixels.
        image_height: Person texture height in pixels.

    Returns:
        Tuple of (width, height) for feet-anchored avatar drawing.
    """
    scaled_h = 2 * screen_cursor_radius(settings)
    scaled_w = max(1, int(scaled_h * image_width / image_height))
    return scaled_w, scaled_h


def radius_from_center(
    logical_x: float, logical_y: float, center_x: float, center_y: float
) -> float:
    """Return circle radius from centre to a logical point, with a minimum.

    Args:
        logical_x: Pointer logical x.
        logical_y: Pointer logical y.
        center_x: Circle centre logical x.
        center_y: Circle centre logical y.

    Returns:
        Radius in logical units, at least half of ``TARGET_MIN_LOGICAL_SPAN``.
    """
    min_radius = TARGET_MIN_LOGICAL_SPAN / 2.0
    dist = math.sqrt((logical_x - center_x) ** 2 + (logical_y - center_y) ** 2)
    return max(min_radius, dist)


def logical_rect_to_viewport_bounds(
    min_pt: tuple[float, float],
    max_pt: tuple[float, float],
    cx: float,
    cy: float,
    zoom: float,
    flip_horizontal: bool,
    flip_vertical: bool,
) -> tuple[float, float, float, float]:
    """Convert logical rect corners to viewport min/max x/y (order-normalized).

    Args:
        min_pt: Logical minimum corner (x, y).
        max_pt: Logical maximum corner (x, y).
        cx: Viewport centre x in pixels.
        cy: Viewport centre y in pixels.
        zoom: Canvas zoom factor.
        flip_horizontal: Whether horizontal axis is flipped.
        flip_vertical: Whether vertical axis is flipped.

    Returns:
        Tuple ``(min_vx, min_vy, max_vx, max_vy)`` in viewport pixels.
    """
    vx0, vy0 = logical_to_viewport(
        min_pt[0], min_pt[1], cx, cy, zoom, flip_horizontal, flip_vertical
    )
    vx1, vy1 = logical_to_viewport(
        max_pt[0], max_pt[1], cx, cy, zoom, flip_horizontal, flip_vertical
    )
    return min(vx0, vx1), min(vy0, vy1), max(vx0, vx1), max(vy0, vy1)


def pick_rect_edge(
    mx: float,
    my: float,
    target: dict[str, Any],
    cx: float,
    cy: float,
    settings: Settings,
) -> RectEdge:
    """Return the viewport edge nearest to a point for a rectangular target.

    Args:
        mx: Viewport pointer x.
        my: Viewport pointer y.
        target: Rect target dict with ``min`` and ``max`` keys.
        cx: Viewport centre x in pixels.
        cy: Viewport centre y in pixels.
        settings: Application settings (zoom and axis flips).

    Returns:
        One of ``left``, ``right``, ``top``, or ``bottom``.
    """
    min_vx, min_vy, max_vx, max_vy = logical_rect_to_viewport_bounds(
        target["min"],
        target["max"],
        cx,
        cy,
        settings.zoom_factor,
        settings.flip_horizontal,
        settings.flip_vertical,
    )
    tol = TARGET_EDGE_HIT_TOLERANCE
    inside = min_vx - tol <= mx <= max_vx + tol and min_vy - tol <= my <= max_vy + tol
    if not inside:
        return "left"
    dists = {
        "left": abs(mx - min_vx),
        "right": abs(mx - max_vx),
        "top": abs(my - min_vy),
        "bottom": abs(my - max_vy),
    }
    return min(dists, key=dists.get)


def trail_size_fraction(index: int, count: int) -> float:
    """Return normalized trail age fraction for index ``index`` of ``count`` points.

    Args:
        index: Trail point index (1-based in draw loops).
        count: Total number of trail coordinates.

    Returns:
        Fraction in ``(0, 1]`` for sizing and fade.
    """
    if count <= 0:
        return 1.0
    return index / count


def trail_stamp_alpha(frac: float) -> int:
    """Return alpha for a trail stamp at age fraction ``frac``.

    Args:
        frac: Normalized age in ``[0, 1]``.

    Returns:
        Alpha value matching circle trail (fixed 200).
    """
    return 200
