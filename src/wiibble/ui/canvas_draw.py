"""Canvas and viewport drawing for WIIBBLE (Dear PyGui drawlist API)."""

from __future__ import annotations

import logging
import math
import time

import dearpygui.dearpygui as dpg

import wiibble.ui.theme as _theme_module
from wiibble.features.data_processing import logical_to_viewport
from wiibble.features.sts_counter import sts_flank_offset_fraction
from wiibble.ui.cursor_geometry import (
    avatar_draw_size,
    screen_cursor_radius,
)
from wiibble.ui.draw_helpers import (
    crisp_icon_text,
    crisp_text,
    measure_crisp_text_width,
)
from wiibble.ui.textures import (
    get_connection_texture_tag,
    get_person_image_size,
    get_wii_texture_tag,
)
from wiibble.ui.theme import (
    BBOX_COLOR,
    BBOX_THICKNESS,
    CALIB_BG_COLOR,
    CANVAS_BG,
    CANVAS_CENTRE_DOT,
    CANVAS_CENTRE_R,
    CANVAS_LINE,
    CANVAS_LINE_DASH,
    CANVAS_LINE_GAP,
    CANVAS_LINE_W,
    CURSOR_COLOR,
    ICON_INFINITY,
    TRAIL_COLOR_BASE,
)
from wiibble.utils.constants import (
    RECORDING_INDICATOR_DOT_RADIUS,
    RECORDING_INDICATOR_LIMIT_FONT_SIZE,
    RECORDING_INDICATOR_RIGHT_MARGIN,
    RECORDING_INDICATOR_SPACING,
    RECORDING_INDICATOR_TIMER_FONT_SIZE,
    RECORDING_INDICATOR_TIMER_GAP,
    RECORDING_INDICATOR_Y,
)

log = logging.getLogger(__name__)

# Calibration screen layout (fractions of canvas width/height)
CALIB_IMG_CENTRE_X = 0.25
CALIB_IMG_HEIGHT = 0.75
CALIB_IMG_VERT = 0.55
CALIB_TEXT_X = 0.57
CALIB_TEXT_TOP = 0.28
CALIB_TEXT_FONT = 0.065
CALIB_TEXT_LINE_H = 1.3
CALIB_ARC_CENTRE_X = 0.62
CALIB_ARC_CENTRE_Y = 0.41
CALIB_ARC_RADIUS = 0.18
CALIB_ARC_THICKNESS = 5
CALIB_ARC_SEGMENTS = 40
STS_TRANSITION_ZONE_COLOR = (55, 58, 65, 255)

# Aliases used by extracted draw code
_crisp_text = crisp_text
_crisp_icon_text = crisp_icon_text
_measure_crisp_text_width = measure_crisp_text_width


def _draw_canvas_counter(
    dl,
    center_x: float,
    label_y: float,
    counter_y: float,
    count: int,
    *,
    label: str = "",
    counter_font_size: int = 90,
    flash_active: bool = False,
) -> None:
    """Draw a large on-canvas counter with an optional label above the digits.

    Args:
        dl: Dear PyGui drawlist parent.
        center_x: Horizontal centre of the counter in pixels.
        label_y: Top y of the optional label row.
        counter_y: Top y of the counter digits.
        count: Integer value to display.
        label: Label drawn above the digits when non-empty.
        counter_font_size: Font size for the count.
        flash_active: When True, use the STS rep flash colour.
    """
    label_font_size = 32
    if label:
        label_w = _measure_crisp_text_width(label, label_font_size)
        _crisp_text(
            (center_x - label_w / 2, label_y),
            label,
            color=(45, 45, 45, 255),
            size=label_font_size,
            parent=dl,
        )
    counter_str = str(count)
    counter_w = _measure_crisp_text_width(counter_str, counter_font_size)
    counter_color = (40, 160, 80, 255) if flash_active else (20, 20, 20, 255)
    _crisp_text(
        (center_x - counter_w / 2, counter_y),
        counter_str,
        color=counter_color,
        size=counter_font_size,
        parent=dl,
    )


def _draw_avatar_feet_anchored(
    feet_x: float,
    feet_y: float,
    settings,
    parent,
    *,
    size_frac: float = 1.0,
    tint: tuple[int, int, int, int] = (255, 255, 255, 255),
) -> None:
    """Draw the person cursor image with feet at (feet_x, feet_y)."""
    iw, ih = get_person_image_size()
    scaled_w_full, scaled_h_full = avatar_draw_size(settings, iw, ih)
    scaled_w = max(1, int(size_frac * scaled_w_full))
    scaled_h = max(1, int(size_frac * scaled_h_full))
    p1 = (feet_x - scaled_w // 2, feet_y - scaled_h)
    p2 = (feet_x + scaled_w // 2, feet_y)
    dpg.draw_image(
        "person_image",
        p1,
        p2,
        parent=parent,
        color=tint,
    )


def _draw_avatar_trail(coords: list[tuple[float, float]], settings, parent) -> None:
    """Draw avatar-mode trail matching circle trail sizing (black silhouettes)."""
    n = len(coords)
    for i in range(1, n):
        frac = i / n
        tx, ty = coords[i]
        _draw_avatar_feet_anchored(
            tx,
            ty,
            settings,
            parent,
            size_frac=frac,
            tint=(0, 0, 0, 200),
        )


def _sts_symmetric_offset_px(sw: int, pct: float) -> float:
    """Return pixel distance from screen centre for a body-weight percentage."""
    return sts_flank_offset_fraction(pct) * (sw / 2.0)


def _draw_sts_threshold_markers(
    bar_top: float,
    bar_bot: float,
    sw: int,
    settings,
    parent: str,
) -> None:
    """Draw symmetric STS threshold zones on the bottom stats bar.

    Only the band between sit and stand thresholds is filled (dark grey);
    seated (inside sit) and standing (beyond stand) regions stay transparent.

    Args:
        bar_top: Top y of the stats strip.
        bar_bot: Bottom y of the stats strip.
        sw: Viewport width in pixels.
        settings: User settings with STS threshold percentages.
        parent: Dear PyGui drawlist parent tag.
    """
    center_x = sw / 2.0
    dpg.draw_line(
        (center_x, bar_top),
        (center_x, bar_bot),
        color=(120, 120, 120, 220),
        thickness=2,
        parent=parent,
    )

    sit_offset = _sts_symmetric_offset_px(sw, settings.sts_sit_threshold_pct)
    stand_offset = _sts_symmetric_offset_px(sw, settings.sts_stand_threshold_pct)

    if stand_offset > sit_offset + 0.5:
        for x0, x1 in (
            (center_x - stand_offset, center_x - sit_offset),
            (center_x + sit_offset, center_x + stand_offset),
        ):
            dpg.draw_rectangle(
                (x0, bar_top),
                (x1, bar_bot),
                fill=(*STS_TRANSITION_ZONE_COLOR[:3], 140),
                color=STS_TRANSITION_ZONE_COLOR,
                thickness=1,
                parent=parent,
            )


def _format_record_limit(seconds: int | float) -> str:
    """Format the configured recording duration for the indicator cluster."""
    total = int(seconds)
    if total <= 0:
        return ICON_INFINITY
    return f"{total // 60:02d}:{total % 60:02d}"


def _recording_limit_width(limit_seconds: int | float, font_size: int) -> int:
    """Estimate pixel width for the limit label (single icon or mm:ss)."""
    label = _format_record_limit(limit_seconds)
    if label == ICON_INFINITY:
        if _theme_module.FA_ICON_FONT_DRAW is not None:
            try:
                w, _ = dpg.get_text_size(label, font=_theme_module.FA_ICON_FONT_DRAW)
                return int(w * (font_size / 100.0))
            except Exception:
                pass
        return int(font_size * 0.85)
    return int(_measure_crisp_text_width(label, font_size))


def _draw_recording_limit_text(
    limit_seconds: int | float,
    *,
    x_limit: float,
    dot_cy: float,
    font_size: int,
    color: tuple,
    parent,
) -> None:
    """Draw the duration limit to the right of the record button."""
    y = _recording_indicator_text_y(font_size, dot_cy)
    label = _format_record_limit(limit_seconds)
    if label == ICON_INFINITY:
        _crisp_icon_text((x_limit, y), label, color, font_size, parent)
    else:
        _crisp_text((x_limit, y), label, color, font_size, parent)


def _recording_indicator_text_y(font_size: int, dot_cy: float) -> float:
    """Return a y coordinate that vertically centres text on the record button."""
    return dot_cy - font_size // 2


def _recording_indicator_layout(sw: int, limit_seconds: int | float = 0) -> dict:
    """Return shared layout metrics for the timer, record button, and limit label."""
    dot_radius = RECORDING_INDICATOR_DOT_RADIUS
    limit_font = RECORDING_INDICATOR_LIMIT_FONT_SIZE
    limit_w = _recording_limit_width(limit_seconds, limit_font)
    # Anchor button + limit from the right; elapsed timer grows left from the button.
    dot_cx = (
        sw
        - RECORDING_INDICATOR_RIGHT_MARGIN
        - limit_w
        - RECORDING_INDICATOR_SPACING
        - dot_radius
    )
    dot_cy = RECORDING_INDICATOR_Y + dot_radius
    x_limit = dot_cx + dot_radius + RECORDING_INDICATOR_SPACING
    return {
        "x_limit": x_limit,
        "dot_cx": dot_cx,
        "dot_cy": dot_cy,
        "dot_radius": dot_radius,
        "timer_font_size": RECORDING_INDICATOR_TIMER_FONT_SIZE,
        "limit_font_size": limit_font,
    }


def _elapsed_timer_x(
    timer_str: str, font_size: int, dot_cx: float, dot_radius: float
) -> float:
    """Right-align the elapsed timer immediately left of the record button."""
    width = _measure_crisp_text_width(timer_str, font_size)
    return dot_cx - dot_radius - RECORDING_INDICATOR_TIMER_GAP - width


def draw_step_instruction(
    dl, step: str, counter: int, max_count: int, app_state
) -> None:
    """
    Draw the 'Step ON' or 'Step OFF' calibration screen.
    Reads live viewport dimensions so layout is always correct after resize.
    All proportions are defined in the LAYOUT constants at the top of this file.
    """
    # Read live viewport — not app_state which lags one frame on resize
    sw = dpg.get_viewport_width()
    sh = dpg.get_viewport_height()

    dpg.draw_rectangle(
        (0, 0), (sw, sh), fill=CALIB_BG_COLOR, color=CALIB_BG_COLOR, parent=dl
    )

    tag = get_wii_texture_tag(1 if step == "on" else 0)
    cfg = dpg.get_item_configuration(tag)
    iw_orig, ih_orig = cfg["width"], cfg["height"]
    scaled_h = int(CALIB_IMG_HEIGHT * sh)
    scaled_w = int(scaled_h * iw_orig / ih_orig)
    img_x = int(sw * CALIB_IMG_CENTRE_X - scaled_w // 2)
    img_y = int(sh * CALIB_IMG_VERT - scaled_h // 2)
    dpg.draw_image(tag, (img_x, img_y), (img_x + scaled_w, img_y + scaled_h), parent=dl)

    font_size = int(sh * CALIB_TEXT_FONT)
    text_x = int(sw * CALIB_TEXT_X)
    text_y = int(sh * CALIB_TEXT_TOP)
    line_h = int(font_size * CALIB_TEXT_LINE_H)

    _crisp_text(
        (text_x, text_y), "Step", color=(250, 250, 250, 255), size=font_size, parent=dl
    )
    _crisp_text(
        (text_x, text_y + line_h),
        "ON" if step == "on" else "OFF",
        color=(0, 250, 0, 255) if step == "on" else (250, 0, 0, 255),
        size=font_size,
        parent=dl,
    )
    _crisp_text(
        (text_x, text_y + line_h * 2),
        "the board",
        color=(250, 250, 250, 255),
        size=font_size,
        parent=dl,
    )
    if step == "on":
        _crisp_text(
            (text_x, text_y + line_h * 4),
            "and stand still",
            color=(250, 250, 250, 255),
            size=font_size,
            parent=dl,
        )

    _draw_arc(dl, sw, sh, counter, max_count, step)


def draw_reference_weight_instruction(
    dl, reference_kg: float, counter: int, max_count: int, app_state
) -> None:
    """Draw the place-reference-weight calibration screen."""
    sw = dpg.get_viewport_width()
    sh = dpg.get_viewport_height()

    dpg.draw_rectangle(
        (0, 0), (sw, sh), fill=CALIB_BG_COLOR, color=CALIB_BG_COLOR, parent=dl
    )

    tag = get_wii_texture_tag(2)
    cfg = dpg.get_item_configuration(tag)
    iw_orig, ih_orig = cfg["width"], cfg["height"]
    scaled_h = int(CALIB_IMG_HEIGHT * sh)
    scaled_w = int(scaled_h * iw_orig / ih_orig)
    img_x = int(sw * CALIB_IMG_CENTRE_X - scaled_w // 2)
    img_y = int(sh * CALIB_IMG_VERT - scaled_h // 2)
    dpg.draw_image(tag, (img_x, img_y), (img_x + scaled_w, img_y + scaled_h), parent=dl)

    font_size = int(sh * CALIB_TEXT_FONT)
    text_x = int(sw * CALIB_TEXT_X)
    text_y = int(sh * CALIB_TEXT_TOP)
    line_h = int(font_size * CALIB_TEXT_LINE_H)

    _crisp_text(
        (text_x, text_y), "Place", color=(250, 250, 250, 255), size=font_size, parent=dl
    )
    _crisp_text(
        (text_x, text_y + line_h),
        f"{reference_kg:.0f} kg",
        color=(0, 250, 0, 255),
        size=font_size,
        parent=dl,
    )
    _crisp_text(
        (text_x, text_y + line_h * 2),
        "on the board",
        color=(250, 250, 250, 255),
        size=font_size,
        parent=dl,
    )
    _crisp_text(
        (text_x, text_y + line_h * 4),
        "and keep still",
        color=(250, 250, 250, 255),
        size=font_size,
        parent=dl,
    )

    _draw_arc(dl, sw, sh, counter, max_count, "on")


def _draw_arc(dl, sw, sh, counter: int, max_count: int, step: str) -> None:
    """
    Draw a clockwise progress arc from 12 o'clock using line segments.
    sw/sh must be live viewport dimensions (passed from draw_step_instruction).
    All proportions are defined in the LAYOUT constants at the top of this file.
    """
    cx = int(sw * CALIB_ARC_CENTRE_X)
    cy = int(sh * CALIB_ARC_CENTRE_Y)
    radius = int(sh * CALIB_ARC_RADIUS)
    color = (0, 250, 0, 255) if step == "on" else (250, 0, 0, 255)
    sweep = 2 * math.pi * counter / max_count if max_count > 0 else 0
    segs = max(1, int(sweep * CALIB_ARC_SEGMENTS))
    start = -math.pi / 2  # 12 o'clock

    for i in range(segs):
        a0 = start + i * sweep / segs
        a1 = start + (i + 1) * sweep / segs
        x0 = cx + radius * math.cos(a0)
        y0 = cy + radius * math.sin(a0)
        x1 = cx + radius * math.cos(a1)
        y1 = cy + radius * math.sin(a1)
        dpg.draw_line(
            (x0, y0), (x1, y1), color=color, thickness=CALIB_ARC_THICKNESS, parent=dl
        )


def draw_connection_screen(dl, app_state) -> None:
    """Draw the 'Trying to connect' screen."""
    sw, sh = app_state.screen_width, app_state.screen_height
    dpg.draw_rectangle(
        (0, 0), (sw, sh), fill=CALIB_BG_COLOR, color=CALIB_BG_COLOR, parent=dl
    )
    font_size = int(sh * 0.06)
    mid_x = sw / 2.5
    mid_y = sh / 2.9
    _crisp_text(
        (mid_x, mid_y),
        "Trying to connect...",
        color=(250, 250, 250, 255),
        size=font_size,
        parent=dl,
    )


def draw_connection_failed_screen(dl, app_state) -> None:
    """Draw the 'Failed to connect' screen with checklist."""
    sw, sh = app_state.screen_width, app_state.screen_height
    dpg.draw_rectangle(
        (0, 0), (sw, sh), fill=CALIB_BG_COLOR, color=CALIB_BG_COLOR, parent=dl
    )

    cfg = dpg.get_item_configuration(get_connection_texture_tag())
    iw_orig, ih_orig = cfg["width"], cfg["height"]
    scaled_h = int(0.8 * sh)
    scaled_w = int(scaled_h * iw_orig / ih_orig)
    img_x = sw // 2 - scaled_w // 2
    img_y = sh // 2 - scaled_h // 2
    dpg.draw_image(
        get_connection_texture_tag(),
        (img_x, img_y),
        (img_x + scaled_w, img_y + scaled_h),
        parent=dl,
    )

    font_size = int(sh * 0.05)
    mx = sw * 0.12
    my = sh / 2.9
    lines = [
        ("Failed to connect", (250, 0, 0, 255)),
        ("Check the following:", (250, 250, 250, 255)),
        ("  1. Bluetooth is enabled on your computer", (250, 250, 250, 255)),
        ("  2. The board is paired to your computer", (250, 250, 250, 255)),
        ("  3. The board is on and blinking blue", (250, 250, 250, 255)),
        ("Press Enter to try again", (250, 250, 250, 255)),
    ]
    for i, (text, color) in enumerate(lines):
        _crisp_text(
            (mx, my + i * font_size * 1.4), text, color=color, size=font_size, parent=dl
        )


def dashed_line_segments(p1, p2, dash=CANVAS_LINE_DASH, gap=CANVAS_LINE_GAP):
    """Return dash segment endpoints along the line from p1 to p2."""
    x0, y0 = p1
    x1, y1 = p2
    dx = x1 - x0
    dy = y1 - y0
    length = math.hypot(dx, dy)
    if length < 1e-6:
        return []
    ux, uy = dx / length, dy / length
    segments = []
    pos = 0.0
    while pos < length:
        end = min(pos + dash, length)
        segments.append(
            ((x0 + ux * pos, y0 + uy * pos), (x0 + ux * end, y0 + uy * end))
        )
        pos = end + gap
    return segments


def _draw_dashed_line(
    p1, p2, *, color, thickness, parent, dash=CANVAS_LINE_DASH, gap=CANVAS_LINE_GAP
):
    """Draw a dashed line from repeated solid segments (no native dash)."""
    for seg_start, seg_end in dashed_line_segments(p1, p2, dash=dash, gap=gap):
        dpg.draw_line(
            seg_start, seg_end, color=color, thickness=thickness, parent=parent
        )


def _logical_rect_viewport_bounds(
    min_pt: tuple[float, float],
    max_pt: tuple[float, float],
    cx: float,
    cy: float,
    zoom: float,
    flip_horizontal: bool,
    flip_vertical: bool,
) -> tuple[float, float, float, float]:
    """Convert logical rect corners to viewport min/max x/y (order-normalized)."""
    vx0, vy0 = logical_to_viewport(
        min_pt[0], min_pt[1], cx, cy, zoom, flip_horizontal, flip_vertical
    )
    vx1, vy1 = logical_to_viewport(
        max_pt[0], max_pt[1], cx, cy, zoom, flip_horizontal, flip_vertical
    )
    return min(vx0, vx1), min(vy0, vy1), max(vx0, vx1), max(vy0, vy1)


def _target_hit_at_point(
    target,
    ball_x: float,
    ball_y: float,
    cx: float,
    cy: float,
    zoom: float,
    flip_horizontal: bool,
    flip_vertical: bool,
) -> bool:
    """Return True when viewport point (ball_x, ball_y) is inside the target."""
    if isinstance(target, dict) and target.get("shape") == "rect":
        min_vx, min_vy, max_vx, max_vy = _logical_rect_viewport_bounds(
            target["min"], target["max"], cx, cy, zoom, flip_horizontal, flip_vertical
        )
        return min_vx <= ball_x <= max_vx and min_vy <= ball_y <= max_vy
    if isinstance(target, dict):
        lx, ly = target["center"]
        logical_radius = target.get("radius", 5.0)
    else:
        lx, ly = target
        logical_radius = 5.0
    vx, vy = logical_to_viewport(lx, ly, cx, cy, zoom, flip_horizontal, flip_vertical)
    scaled_radius = logical_radius * zoom
    dist = math.sqrt((vx - ball_x) ** 2 + (vy - ball_y) ** 2)
    return dist < scaled_radius


def update_target_dwell(
    app_state, settings, hit_by_index: dict[int, bool], *, dt: float | None = None
) -> None:
    """Accumulate per-target dwell time and increment counter at threshold."""
    if dt is None:
        now = time.perf_counter()
        if app_state._target_dwell_last_tick <= 0:
            dt = 0.0
        else:
            dt = now - app_state._target_dwell_last_tick
        app_state._target_dwell_last_tick = now

    valid_indices = set(hit_by_index.keys())
    elapsed = app_state._target_dwell_elapsed
    disarmed = app_state._target_dwell_disarmed

    for idx in list(elapsed.keys()):
        if idx not in valid_indices:
            del elapsed[idx]
    disarmed.intersection_update(valid_indices)

    dwell_seconds = settings.target_dwell_seconds

    for idx, hit in hit_by_index.items():
        if hit:
            if idx in disarmed:
                continue
            if dwell_seconds <= 0:
                app_state.target_hit_count += 1
                disarmed.add(idx)
                elapsed.pop(idx, None)
                log.info(
                    "Target hit registered (count=%d, index=%d)",
                    app_state.target_hit_count,
                    idx,
                )
                continue
            elapsed[idx] = elapsed.get(idx, 0.0) + dt
            if elapsed[idx] >= dwell_seconds:
                app_state.target_hit_count += 1
                elapsed.pop(idx, None)
                disarmed.add(idx)
                log.info(
                    "Target hit registered (count=%d, index=%d)",
                    app_state.target_hit_count,
                    idx,
                )
        else:
            elapsed.pop(idx, None)
            disarmed.discard(idx)


def draw_main_screen(
    dl,
    corners: dict,
    ball_x: int,
    ball_y: int,
    curr_weight: float,
    max_x,
    max_y,
    min_x,
    min_y,
    app_state,
    settings,
    pan_offset_x: float = 0.0,
    pan_offset_y: float = 0.0,
    toolbar_visible: bool = False,
    toolbar_enabled: bool = False,
) -> None:
    """
    Draw one frame of the main balance display onto drawlist dl.

    ball_x/ball_y are in full viewport coordinates (already include pan offset).
    pan_offset_x/y shift crosshairs and bounding box so the whole canvas pans
    together — the user's position and the grid move as one unit.
    Canvas fills entire viewport; toolbar windows float on top.
    sw/sh are full viewport dimensions. Toolbar floats on top.
    """
    sw, sh = app_state.screen_width, app_state.screen_height

    # Canvas centre — shifted by pan offset
    cx = sw // 2 + pan_offset_x
    cy = sh // 2 + pan_offset_y

    # Background — full viewport
    dpg.draw_rectangle((0, 0), (sw, sh), fill=CANVAS_BG, color=CANVAS_BG, parent=dl)

    # Global axes — solid crosshairs at canvas centre
    line_w = CANVAS_LINE_W
    if settings.show_global_axes:
        dpg.draw_line((0, cy), (sw, cy), color=CANVAS_LINE, thickness=line_w, parent=dl)
        dpg.draw_line((cx, 0), (cx, sh), color=CANVAS_LINE, thickness=line_w, parent=dl)
        dpg.draw_circle(
            (cx, cy),
            CANVAS_CENTRE_R,
            color=CANVAS_CENTRE_DOT,
            fill=CANVAS_CENTRE_DOT,
            parent=dl,
        )

    # Bounding box — max_x/min_x are relative coordinate extents (not viewport coords).
    if settings.show_bbox:
        dpg.draw_rectangle(
            (cx + min_x, cy + min_y),
            (cx + max_x, cy + max_y),
            color=BBOX_COLOR,
            thickness=BBOX_THICKNESS,
            parent=dl,
        )

    # Local axes — dotted crosshairs centred on sway bbox, bounded to bbox edges
    if settings.show_local_axes:
        bbox_w = max_x - min_x
        bbox_h = max_y - min_y
        if bbox_w >= 1 and bbox_h >= 1:
            local_cx = cx + (min_x + max_x) / 2
            local_cy = cy + (min_y + max_y) / 2
            _draw_dashed_line(
                (cx + min_x, local_cy),
                (cx + max_x, local_cy),
                color=CANVAS_LINE,
                thickness=line_w,
                parent=dl,
            )
            _draw_dashed_line(
                (local_cx, cy + min_y),
                (local_cx, cy + max_y),
                color=CANVAS_LINE,
                thickness=line_w,
                parent=dl,
            )

    # Targets (clicked locations — stored in logical/content coords)
    cx = sw // 2 + pan_offset_x
    cy = sh // 2 + pan_offset_y
    zoom = settings.zoom_factor
    flip_h = settings.flip_horizontal
    flip_v = settings.flip_vertical
    target_hits: dict[int, bool] = {}
    for idx, target in enumerate(app_state.clicked_locations):
        if isinstance(target, dict) and target.get("shape") == "rect":
            min_vx, min_vy, max_vx, max_vy = _logical_rect_viewport_bounds(
                target["min"], target["max"], cx, cy, zoom, flip_h, flip_v
            )
            hit = _target_hit_at_point(
                target, ball_x, ball_y, cx, cy, zoom, flip_h, flip_v
            )
            target_hits[idx] = hit
            fill = (0, 255, 0, 200) if hit else (255, 0, 0, 200)
            dpg.draw_rectangle(
                (min_vx, min_vy), (max_vx, max_vy), color=fill, fill=fill, parent=dl
            )
            continue
        if isinstance(target, dict):
            (lx, ly) = target["center"]
            logical_radius = target.get("radius", 5.0)
        else:
            (lx, ly) = target
            logical_radius = 5.0
        vx, vy = logical_to_viewport(lx, ly, cx, cy, zoom, flip_h, flip_v)
        scaled_radius = logical_radius * zoom
        hit = _target_hit_at_point(target, ball_x, ball_y, cx, cy, zoom, flip_h, flip_v)
        target_hits[idx] = hit
        fill = (0, 255, 0, 200) if hit else (255, 0, 0, 200)
        dpg.draw_circle(
            (vx, vy), max(1.0, scaled_radius), color=fill, fill=fill, parent=dl
        )

    update_target_dwell(app_state, settings, target_hits)

    # Draw target-in-progress (preview)
    tip = getattr(app_state, "target_in_progress", None)
    if tip is not None:
        if tip.get("shape") == "rect":
            min_vx, min_vy, max_vx, max_vy = _logical_rect_viewport_bounds(
                tip["min"], tip["max"], cx, cy, zoom, flip_h, flip_v
            )
            dpg.draw_rectangle(
                (min_vx, min_vy),
                (max_vx, max_vy),
                color=(0, 200, 255, 180),
                fill=(0, 200, 255, 60),
                parent=dl,
            )
        else:
            (lx, ly) = tip["center"]
            logical_radius = tip.get("radius", 5.0)
            vx, vy = logical_to_viewport(lx, ly, cx, cy, zoom, flip_h, flip_v)
            scaled_radius = logical_radius * zoom
            dpg.draw_circle(
                (vx, vy),
                scaled_radius,
                color=(0, 200, 255, 180),
                fill=(0, 200, 255, 60),
                parent=dl,
            )

    # Trail (S2: sliced to trail_length; coords are in viewport space)
    coords = (
        app_state.historical_coords[-settings.trail_length :]
        if settings.trail_length > 0
        else []
    )
    n = len(coords)
    screen_radius = screen_cursor_radius(settings)
    if settings.cursor_mode == "avatar":
        _draw_avatar_trail(coords, settings, dl)
    else:
        for i in range(1, n):
            frac = i / n
            tc = (
                int(frac * TRAIL_COLOR_BASE[0]),
                int(frac * TRAIL_COLOR_BASE[1]),
                int(frac * TRAIL_COLOR_BASE[2]),
                200,
            )
            radius = max(1, int(i * screen_radius / n))
            dpg.draw_circle(coords[i], radius, color=tc, fill=tc, parent=dl)

    # Cursor (S1) — ball_x/ball_y in viewport coords
    if settings.cursor_mode == "avatar":
        _draw_avatar_feet_anchored(ball_x, ball_y, settings, dl)
    else:
        dpg.draw_circle(
            (ball_x, ball_y),
            screen_radius,
            color=CURSOR_COLOR,
            fill=CURSOR_COLOR,
            parent=dl,
        )

    # Weight bar and stats text are both drawn on stats_dl in app.py
    # so they render above the canvas layer in the correct order.

    # --- Overlays: Countdown, Recording Indicator, and Stopwatch Timer ---
    # Draw countdown overlay (centered text) — crisp large number
    if getattr(app_state, "is_countdown", False):
        _crisp_text(
            (sw * 0.49, sh * 0.4),
            f"{getattr(app_state, 'countdown_value', '')}",
            color=(255, 0, 0, 255),
            size=100,
            parent=dl,
        )

    # On-canvas rep counters — STS left, target hits right (or centred when alone)
    show_sts_counter = (
        settings.sts_enabled and settings.sts_show_counter and toolbar_enabled
    )
    show_target_counter = settings.show_target_counter and toolbar_enabled
    both_counters = show_sts_counter and show_target_counter
    counter_font_size = 72 if both_counters else 90
    label_y = sh * 0.055
    counter_y = sh * 0.10

    if show_sts_counter:
        flash_active = time.time() < getattr(app_state, "sts_rep_flash_until", 0.0)
        sts_x = sw * 0.22 if both_counters else sw / 2
        _draw_canvas_counter(
            dl,
            sts_x,
            label_y,
            counter_y,
            app_state.sts_rep_count,
            label="REPS",
            counter_font_size=counter_font_size,
            flash_active=flash_active,
        )
    if show_target_counter:
        target_x = sw * 0.78 if both_counters else sw / 2
        _draw_canvas_counter(
            dl,
            target_x,
            label_y,
            counter_y,
            app_state.target_hit_count,
            label="HITS",
            counter_font_size=counter_font_size,
        )

    # Recording indicator cluster: elapsed timer (while recording) + limit (always).
    if toolbar_enabled:
        limit_seconds = (
            app_state.record_duration
            if getattr(app_state, "recording_indicator", False)
            else settings.record_duration
        )
        layout = _recording_indicator_layout(sw, limit_seconds)
        limit_color = (255, 0, 0, 255)
        _draw_recording_limit_text(
            limit_seconds,
            x_limit=layout["x_limit"],
            dot_cy=layout["dot_cy"],
            font_size=layout["limit_font_size"],
            color=limit_color,
            parent=dl,
        )

        if getattr(app_state, "recording_indicator", False):
            elapsed = getattr(app_state, "stopwatch_elapsed", 0.0)
            mins = int(elapsed // 60)
            secs = elapsed % 60
            timer_str = f"{mins:02d}:{secs:04.1f}"
            _crisp_text(
                (
                    _elapsed_timer_x(
                        timer_str,
                        layout["timer_font_size"],
                        layout["dot_cx"],
                        layout["dot_radius"],
                    ),
                    _recording_indicator_text_y(
                        layout["timer_font_size"], layout["dot_cy"]
                    ),
                ),
                timer_str,
                color=(255, 0, 0, 255),
                size=layout["timer_font_size"],
                parent=dl,
            )

    # Toast overlay — shown briefly after a recording is saved
    if time.time() < getattr(app_state, "toast_until", 0.0):
        msg = getattr(app_state, "toast_message", "")
        toast_h = 44
        margin = 20
        toast_y = 55
        dpg.draw_rectangle(
            (margin, toast_y),
            (sw - margin, toast_y + toast_h),
            fill=(30, 36, 48, 210),
            color=(80, 200, 120, 255),
            thickness=2,
            rounding=6,
            parent=dl,
        )
        _crisp_text(
            (sw // 2 - 80, toast_y + 7),
            msg,
            color=(80, 200, 120, 255),
            size=28,
            parent=dl,
        )
