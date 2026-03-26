# ui.py
# All rendering via Dear PyGui drawlist API.
# The viewport_drawlist draws directly onto the viewport background — no
# window chrome around the canvas. UI controls sit in a separate overlay window.

import math
import dearpygui.dearpygui as dpg
from resources import IMAGE_PATHS, CONNECTION_PATH, PERSON_IMAGE_PATH
from theme import (CANVAS_BG, CANVAS_LINE, CANVAS_LINE_W, CANVAS_CENTRE_DOT,
                   CANVAS_CENTRE_R, BBOX_COLOR, BBOX_THICKNESS, CURSOR_COLOR, TRAIL_COLOR_BASE, CALIB_BG_COLOR,
                   bind_text_font,
                   )

# ---------------------------------------------------------------------------
# Layout constants — all proportional to viewport dimensions.
# Change a value here and it propagates everywhere.
# ---------------------------------------------------------------------------
STATS_STRIP_H     = 50      # height of bottom stats strip in pixels
STATS_FONT_SCALE  = 0.055   # stats font size as fraction of viewport height
STATS_FONT_MIN    = 24      # minimum stats font size in pixels

# Calibration screen (fractions of canvas width/height)
CALIB_IMG_CENTRE_X  = 0.25
CALIB_IMG_HEIGHT    = 0.75
CALIB_IMG_VERT      = 0.55
CALIB_TEXT_X        = 0.57
CALIB_TEXT_TOP      = 0.28
CALIB_TEXT_FONT     = 0.065
CALIB_TEXT_LINE_H   = 1.3
CALIB_ARC_CENTRE_X  = 0.65
CALIB_ARC_CENTRE_Y  = 0.45
CALIB_ARC_RADIUS    = 0.22
CALIB_ARC_THICKNESS = 5
CALIB_ARC_SEGMENTS  = 40


# ---------------------------------------------------------------------------
# Crisp draw_text helper
# ---------------------------------------------------------------------------

def _crisp_text(pos, text: str, color: tuple, size: int, parent) -> int:
    """
    Drop-in replacement for dpg.draw_text() that binds TEXT_FONT to the
    created item so ImGui downscales the 100px atlas glyph instead of
    upscaling the default ~13px bitmap font.

    Returns the item tag (same as dpg.draw_text).
    """
    tag = dpg.draw_text(pos, text, color=color, size=size, parent=parent)
    bind_text_font(tag)
    return tag


# ---------------------------------------------------------------------------
# Texture registry — images must be loaded into DPG's texture system
# ---------------------------------------------------------------------------

_textures_loaded = False
_wii_texture_tags = []
_person_texture_tag = "person_image"
_connection_texture_tag = "connection_image"


def ensure_textures_loaded():
    """Load all images into DPG texture registry on first call."""
    global _textures_loaded, _wii_texture_tags
    if _textures_loaded:
        return

    with dpg.texture_registry():
        # Calibration screen images (wii0, wii1, wii2)
        for i, path in enumerate(IMAGE_PATHS):
            w, h, _, data = dpg.load_image(path)
            tag = f"wii_image_{i}"
            dpg.add_static_texture(w, h, data, tag=tag)
            _wii_texture_tags.append(tag)

        # Person cursor image
        w, h, _, data = dpg.load_image(PERSON_IMAGE_PATH)
        dpg.add_static_texture(w, h, data, tag=_person_texture_tag)

        # Connection failed image
        w, h, _, data = dpg.load_image(CONNECTION_PATH)
        dpg.add_static_texture(w, h, data, tag=_connection_texture_tag)

    _textures_loaded = True


def get_wii_image_size(index: int) -> tuple:
    """Return (width, height) of a wii calibration image."""
    return dpg.get_item_configuration(_wii_texture_tags[index])["width"], \
           dpg.get_item_configuration(_wii_texture_tags[index])["height"]


def get_person_image_size() -> tuple:
    cfg = dpg.get_item_configuration(_person_texture_tag)
    return cfg["width"], cfg["height"]


# ---------------------------------------------------------------------------
# Calibration screens — drawn to viewport_drawlist each frame
# ---------------------------------------------------------------------------

def draw_step_instruction(dl, step: str, counter: int, max_count: int, app_state) -> None:
    """
    Draw the 'Step ON' or 'Step OFF' calibration screen.
    Reads live viewport dimensions so layout is always correct after resize.
    All proportions are defined in the LAYOUT constants at the top of this file.
    """
    # Read live viewport — not app_state which lags one frame on resize
    sw = dpg.get_viewport_width()
    sh = dpg.get_viewport_height()

    dpg.draw_rectangle((0, 0), (sw, sh),
                        fill=CALIB_BG_COLOR, color=CALIB_BG_COLOR, parent=dl)

    tag = _wii_texture_tags[2]
    cfg = dpg.get_item_configuration(tag)
    iw_orig, ih_orig = cfg["width"], cfg["height"]
    scaled_h = int(CALIB_IMG_HEIGHT * sh)
    scaled_w = int(scaled_h * iw_orig / ih_orig)
    img_x = int(sw * CALIB_IMG_CENTRE_X - scaled_w // 2)
    img_y = int(sh * CALIB_IMG_VERT - scaled_h // 2)
    dpg.draw_image(tag, (img_x, img_y), (img_x + scaled_w, img_y + scaled_h), parent=dl)

    font_size = int(sh * CALIB_TEXT_FONT)
    text_x    = int(sw * CALIB_TEXT_X)
    text_y    = int(sh * CALIB_TEXT_TOP)
    line_h    = int(font_size * CALIB_TEXT_LINE_H)

    _crisp_text((text_x, text_y),            "Step",
                color=(250, 250, 250, 255), size=font_size, parent=dl)
    _crisp_text((text_x, text_y + line_h),   "ON" if step == "on" else "OFF",
                color=(0, 250, 0, 255) if step == "on" else (250, 0, 0, 255),
                size=font_size, parent=dl)
    _crisp_text((text_x, text_y + line_h*2), "the board",
                color=(250, 250, 250, 255), size=font_size, parent=dl)
    if step == "on":
        _crisp_text((text_x, text_y + line_h*4), "and stand still",
                    color=(250, 250, 250, 255), size=font_size, parent=dl)

    _draw_arc(dl, sw, sh, counter, max_count, step)


def _draw_arc(dl, sw, sh, counter: int, max_count: int, step: str) -> None:
    """
    Draw a clockwise progress arc from 12 o'clock using line segments.
    sw/sh must be live viewport dimensions (passed from draw_step_instruction).
    All proportions are defined in the LAYOUT constants at the top of this file.
    """
    cx     = int(sw * CALIB_ARC_CENTRE_X)
    cy     = int(sh * CALIB_ARC_CENTRE_Y)
    radius = int(sh * CALIB_ARC_RADIUS)
    color  = (0, 250, 0, 255) if step == "on" else (250, 0, 0, 255)
    sweep  = 2 * math.pi * counter / max_count if max_count > 0 else 0
    segs   = max(1, int(sweep * CALIB_ARC_SEGMENTS))
    start  = -math.pi / 2  # 12 o'clock

    for i in range(segs):
        a0 = start + i       * sweep / segs
        a1 = start + (i + 1) * sweep / segs
        x0 = cx + radius * math.cos(a0)
        y0 = cy + radius * math.sin(a0)
        x1 = cx + radius * math.cos(a1)
        y1 = cy + radius * math.sin(a1)
        dpg.draw_line((x0, y0), (x1, y1), color=color,
                      thickness=CALIB_ARC_THICKNESS, parent=dl)


def draw_connection_screen(dl, app_state) -> None:
    """Draw the 'Trying to connect' screen."""
    sw, sh = app_state.screen_width, app_state.screen_height
    dpg.draw_rectangle((0, 0), (sw, sh), fill=CALIB_BG_COLOR,
                        color=CALIB_BG_COLOR, parent=dl)
    font_size = int(sh * 0.06)
    mid_x = sw / 2.5
    mid_y = sh / 2.9
    _crisp_text((mid_x, mid_y), "Trying to connect...",
                color=(250, 250, 250, 255), size=font_size, parent=dl)


def draw_connection_failed_screen(dl, app_state) -> None:
    """Draw the 'Failed to connect' screen with checklist."""
    sw, sh = app_state.screen_width, app_state.screen_height
    dpg.draw_rectangle((0, 0), (sw, sh), fill=CALIB_BG_COLOR,
                        color=CALIB_BG_COLOR, parent=dl)

    cfg = dpg.get_item_configuration(_connection_texture_tag)
    iw_orig, ih_orig = cfg["width"], cfg["height"]
    scaled_h = int(0.8 * sh)
    scaled_w = int(scaled_h * iw_orig / ih_orig)
    img_x = sw // 2 - scaled_w // 2
    img_y = sh // 2 - scaled_h // 2
    dpg.draw_image(_connection_texture_tag,
                   (img_x, img_y), (img_x + scaled_w, img_y + scaled_h), parent=dl)

    font_size = int(sh * 0.05)
    mx = sw * 0.12
    my = sh / 2.9
    lines = [
        ("Failed to connect",                              (250, 0,   0,   255)),
        ("Check the following:",                           (250, 250, 250, 255)),
        ("  1. Bluetooth is enabled on your computer",    (250, 250, 250, 255)),
        ("  2. The board is paired to your computer",     (250, 250, 250, 255)),
        ("  3. The board is on and blinking blue",        (250, 250, 250, 255)),
        ("Press Enter to try again",                      (250, 250, 250, 255)),
    ]
    for i, (text, color) in enumerate(lines):
        _crisp_text((mx, my + i * font_size * 1.4), text,
                    color=color, size=font_size, parent=dl)


# ---------------------------------------------------------------------------
# Main balance screen
# ---------------------------------------------------------------------------

def draw_main_screen(dl, corners: dict, ball_x: int, ball_y: int,
                     curr_weight: float, max_x, max_y, min_x, min_y,
                     app_state, settings,
                     pan_offset_x: float = 0.0, pan_offset_y: float = 0.0) -> None:
    """
    Draw one frame of the main balance display onto drawlist dl.

    ball_x/ball_y are in full viewport coordinates (already include pan offset).
    pan_offset_x/y shift crosshairs and bounding box so the whole canvas pans
    together — the user's position and the grid move as one unit.
    Canvas fills entire viewport; toolbar windows float on top.
    sw/sh are full viewport dimensions. Toolbar floats on top.
    """
    sw, sh = app_state.screen_width, app_state.screen_height

    top_right    = corners["top_right"]
    bottom_right = corners["bottom_right"]
    top_left     = corners["top_left"]
    bottom_left  = corners["bottom_left"]

    # Canvas centre — shifted by pan offset
    cx = sw // 2 + pan_offset_x
    cy = sh // 2 + pan_offset_y

    # Background — full viewport
    dpg.draw_rectangle((0, 0), (sw, sh), fill=CANVAS_BG,
                        color=CANVAS_BG, parent=dl)

    # Centre lines
    line_w = CANVAS_LINE_W
    dpg.draw_line((0, cy), (sw, cy), color=CANVAS_LINE, thickness=line_w, parent=dl)
    dpg.draw_line((cx, 0), (cx, sh), color=CANVAS_LINE, thickness=line_w, parent=dl)
    dpg.draw_circle((cx, cy), CANVAS_CENTRE_R, color=CANVAS_CENTRE_DOT,
                    fill=CANVAS_CENTRE_DOT, parent=dl)

    # Target circles (clicked locations — stored in logical/content coords)
    cx = sw // 2 + pan_offset_x
    cy = sh // 2 + pan_offset_y
    # Draw all finalized targets (support both old tuple and new dict format)
    for target in app_state.clicked_locations:
        if isinstance(target, dict):
            (lx, ly) = target["center"]
            logical_radius = target.get("radius", 5.0)
        else:
            (lx, ly) = target
            logical_radius = 5.0
        vx = cx + lx * settings.zoom_factor
        vy = cy + ly * settings.zoom_factor
        scaled_radius = logical_radius * settings.zoom_factor
        dist = math.sqrt((vx - ball_x) ** 2 + (vy - ball_y) ** 2)
        hit = dist < scaled_radius
        fill = (0, 255, 0, 200) if hit else (255, 0, 0, 200)
        dpg.draw_circle((vx, vy), scaled_radius, color=fill, fill=fill, parent=dl)

    # Draw target-in-progress (preview)
    tip = getattr(app_state, "target_in_progress", None)
    if tip is not None:
        (lx, ly) = tip["center"]
        logical_radius = tip.get("radius", 5.0)
        vx = cx + lx * settings.zoom_factor
        vy = cy + ly * settings.zoom_factor
        scaled_radius = logical_radius * settings.zoom_factor
        dpg.draw_circle((vx, vy), scaled_radius, color=(0, 200, 255, 180), fill=(0, 200, 255, 60), parent=dl)

    # Trail (S2: sliced to trail_length; coords are in viewport space)
    coords = app_state.historical_coords[-settings.trail_length:] if settings.trail_length > 0 else []
    n = len(coords)
    for i in range(1, n):
        frac = i / n
        tc = (int(frac * TRAIL_COLOR_BASE[0]),
              int(frac * TRAIL_COLOR_BASE[1]),
              int(frac * TRAIL_COLOR_BASE[2]), 200)
        radius = max(1, int(i * 20 / n))
        dpg.draw_circle(coords[i], radius, color=tc, fill=tc, parent=dl)

    # Cursor (S1) — ball_x/ball_y in viewport coords
    if settings.cursor_mode == "avatar":
        cfg = dpg.get_item_configuration(_person_texture_tag)
        iw, ih = cfg["width"], cfg["height"]
        scaled_h = int(0.1 * sh)
        scaled_w = int(scaled_h * iw / ih)
        p1 = (ball_x - scaled_w // 2, ball_y - scaled_h)
        p2 = (ball_x + scaled_w // 2, ball_y)
        dpg.draw_image(_person_texture_tag, p1, p2, parent=dl)
    else:
        dpg.draw_circle((ball_x, ball_y), 20,
                        color=CURSOR_COLOR, fill=CURSOR_COLOR, parent=dl)

    # Bounding box — max_x/min_x are relative coordinate extents (not viewport coords).
    # They need to be offset by canvas centre (cx, cy) to get viewport coords.
    dpg.draw_rectangle(
        (cx + min_x, cy + min_y),
        (cx + max_x, cy + max_y),
        color=BBOX_COLOR, thickness=BBOX_THICKNESS, parent=dl,
    )

    # Weight bar and stats text are both drawn on stats_dl in app.py
    # so they render above the canvas layer in the correct order.

    # --- Overlays: Countdown, Recording Indicator, and Stopwatch Timer ---
    # Draw countdown overlay (centered text) — crisp large number
    if getattr(app_state, "is_countdown", False):
        _crisp_text((sw//2-30, sh//2-60), f"{getattr(app_state, 'countdown_value', '')}",
                    color=(255, 0, 0, 255), size=100, parent=dl)

    # Draw recording indicator (red dot + REC) and stopwatch timer
    if getattr(app_state, "recording_indicator", False):
        dpg.draw_circle((sw*0.95, 20), 18, color=(255, 0, 0, 255), fill=(255, 0, 0, 200), parent=dl)
        _crisp_text((sw*0.95 + 25, 4), "REC",
                    color=(255, 0, 0, 255), size=32, parent=dl)
        # Stopwatch timer (mm:ss.t)
        elapsed = getattr(app_state, "stopwatch_elapsed", 0.0)
        mins = int(elapsed // 60)
        secs = elapsed % 60
        timer_str = f"{mins:02d}:{secs:04.1f}"
        _crisp_text((sw*0.95 - 150, 4), timer_str,
                    color=(255, 0, 0, 255), size=32, parent=dl)