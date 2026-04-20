# ui.py
# All rendering via Dear PyGui drawlist API.
# The viewport_drawlist draws directly onto the viewport background — no
# window chrome around the canvas. UI controls sit in a separate overlay window.

import math

import dearpygui.dearpygui as dpg

import theme as _theme_module
from constants import (
    FILTER_MAX,
    FILTER_MIN,
    PANEL_BTN_H,
    PANEL_BTN_W,
    PANEL_COMBO_W,
    PANEL_SECTION_SPACING,
    PANEL_SLIDER_W,
    PANEL_TOGGLE_BTN_SIZE,
    PANEL_W,
    ZOOM_MAX,
    ZOOM_MIN,
    ZOOM_SCALE,
)
from resources import CONNECTION_PATH, IMAGE_PATHS, PERSON_IMAGE_PATH
from theme import (
    BAR_GREY_COLOR,
    BBOX_COLOR,
    BBOX_THICKNESS,
    CALIB_BG_COLOR,
    CANVAS_BG,
    CANVAS_CENTRE_DOT,
    CANVAS_CENTRE_R,
    CANVAS_LINE,
    CANVAS_LINE_W,
    CURSOR_COLOR,
    STATS_TEXT_COLOR,
    TRAIL_COLOR_BASE,
    bind_text_font,
    get_stats_bar_color,
)

# ---------------------------------------------------------------------------
# Layout constants — all proportional to viewport dimensions.
# Change a value here and it propagates everywhere.
# ---------------------------------------------------------------------------
STATS_STRIP_H = 50  # height of bottom stats strip in pixels
STATS_FONT_SCALE = 0.055  # stats font size as fraction of viewport height
STATS_FONT_MIN = 24  # minimum stats font size in pixels

# Calibration screen (fractions of canvas width/height)
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
    return dpg.get_item_configuration(_wii_texture_tags[index])[
        "width"
    ], dpg.get_item_configuration(_wii_texture_tags[index])["height"]


def get_person_image_size() -> tuple:
    """Return the width and height of the person cursor texture."""
    cfg = dpg.get_item_configuration(_person_texture_tag)
    return cfg["width"], cfg["height"]


# Cached stats values — stats drawlist only redraws when these change.
# This eliminates the sub-pixel jitter that caused blurry text.
_stats_cache = {"left": -1, "weight": -1, "right": -1}


def build_stats_bar(app_state) -> None:
    """Create or reset the overlay stats drawlist for the main screen."""
    if not dpg.does_item_exist("stats_dl"):
        dpg.add_viewport_drawlist(tag="stats_dl", front=True)
    dpg.delete_item("stats_dl", children_only=True)
    _stats_cache["left"] = -1
    _stats_cache["weight"] = -1
    _stats_cache["right"] = -1


def update_stats_bar(
    perc_left: float, perc_right: float, curr_weight: float, calib_weight: float
) -> None:
    """Draw the live left/right distribution and weight stats overlay."""
    left_val = int(perc_left * 100)
    weight_val = int(curr_weight)
    right_val = int(perc_right * 100)

    if (
        left_val == _stats_cache["left"]
        and weight_val == _stats_cache["weight"]
        and right_val == _stats_cache["right"]
    ):
        return

    _stats_cache["left"] = left_val
    _stats_cache["weight"] = weight_val
    _stats_cache["right"] = right_val

    sw = dpg.get_viewport_width()
    vh = dpg.get_viewport_height()
    font_size = max(STATS_FONT_MIN, int(vh * STATS_FONT_SCALE))
    bar_top = vh - STATS_STRIP_H
    bar_bot = vh
    y = bar_top - font_size - 6

    dpg.delete_item("stats_dl", children_only=True)

    dpg.draw_rectangle(
        (0, bar_top), (sw, bar_bot), fill=BAR_GREY_COLOR, color=BAR_GREY_COLOR, parent="stats_dl"
    )

    percent = curr_weight / calib_weight if calib_weight > 0 else 0
    bar_color = get_stats_bar_color(percent)

    if _stats_cache["weight"] > 0:
        pl = _stats_cache["left"] / 100
        pr = _stats_cache["right"] / 100
    else:
        pl = pr = 0.5
    x0 = sw // 2 - pl * sw // 2
    dpg.draw_rectangle(
        (x0, bar_top), (sw // 2, bar_bot), fill=bar_color, color=bar_color, parent="stats_dl"
    )
    x0 = sw // 2
    x1 = sw // 2 + pr * sw // 2
    dpg.draw_rectangle(
        (x0, bar_top), (x1, bar_bot), fill=bar_color, color=bar_color, parent="stats_dl"
    )

    t = dpg.draw_text(
        (10, y), f"{left_val}%", color=STATS_TEXT_COLOR, size=font_size, parent="stats_dl"
    )
    bind_text_font(t)
    t = dpg.draw_text(
        (sw // 2 - 40, y),
        f"{weight_val} kg",
        color=STATS_TEXT_COLOR,
        size=font_size,
        parent="stats_dl",
    )
    bind_text_font(t)
    t = dpg.draw_text(
        (sw - font_size * 3, y),
        f"{right_val}%",
        color=STATS_TEXT_COLOR,
        size=font_size,
        parent="stats_dl",
    )
    bind_text_font(t)


def build_panel_window(
    screen_height: int,
    toggle_label: str,
    toggle_callback,
    settings_group_builder,
) -> None:
    """Create the left-side settings panel window and populate it with controls."""
    with dpg.window(
        tag="control_panel",
        no_title_bar=True,
        no_resize=True,
        no_move=True,
        no_scrollbar=False,
        no_collapse=True,
        no_scroll_with_mouse=False,
        pos=(0, 0),
        width=PANEL_W,
        height=screen_height,
        show=False,
    ):
        # Panel header row: close button on right, title on left
        with dpg.group(horizontal=True):
            dpg.add_text("Settings")
            dpg.add_spacer(width=PANEL_W - 120)
            dpg.add_button(
                tag="panel_close_btn",
                label=toggle_label,
                callback=toggle_callback,
                width=PANEL_TOGGLE_BTN_SIZE,
                height=PANEL_TOGGLE_BTN_SIZE,
            )
        dpg.add_separator()
        dpg.add_spacer(height=PANEL_SECTION_SPACING)
        with dpg.group(tag="settings_group"):
            settings_group_builder()

    if _theme_module.FA_ICON_FONT is not None:
        dpg.bind_item_font("panel_close_btn", _theme_module.FA_ICON_FONT)


def build_panel_toggle_btn(toggle_label: str, toggle_callback) -> None:
    """Create the floating toggle button shown when the panel is collapsed."""
    if dpg.does_item_exist("panel_toggle_window"):
        dpg.delete_item("panel_toggle_window")

    with dpg.window(
        tag="panel_toggle_window",
        no_title_bar=True,
        no_resize=True,
        no_move=True,
        no_scrollbar=True,
        no_collapse=True,
        no_background=True,
        pos=(4, 4),
        width=PANEL_TOGGLE_BTN_SIZE + 4,
        height=PANEL_TOGGLE_BTN_SIZE + 4,
        show=False,
    ):
        dpg.add_button(
            tag="panel_float_btn",
            label=toggle_label,
            callback=toggle_callback,
            width=PANEL_TOGGLE_BTN_SIZE,
            height=PANEL_TOGGLE_BTN_SIZE,
        )

    if _theme_module.FA_ICON_FONT is not None:
        dpg.bind_item_font("panel_float_btn", _theme_module.FA_ICON_FONT)


def _build_section_header(label: str) -> None:
    """Render a dimly-coloured section label and a separator line."""
    dpg.add_spacer(height=PANEL_SECTION_SPACING)
    with dpg.group(horizontal=True):
        t = dpg.add_text(label)
        # Apply dim text colour to section headings
        with dpg.theme() as _section_theme:
            with dpg.theme_component(dpg.mvText):
                dpg.add_theme_color(
                    dpg.mvThemeCol_Text,
                    _theme_module.C_TEXT_DIM,
                    category=dpg.mvThemeCat_Core,
                )
        dpg.bind_item_theme(t, _section_theme)
    dpg.add_separator()
    dpg.add_spacer(height=PANEL_SECTION_SPACING)


def _cursor_label(settings):
    """Return what the cursor toggle button will switch TO (action label)."""
    return "Switch to Avatar" if settings.cursor_mode == "circle" else "Switch to Circle"


def update_cursor_toggle_label(settings):
    """Update the panel cursor button label to reflect the current mode."""
    dpg.set_item_label("cursor_toggle_btn", _cursor_label(settings))


def _on_cursor_toggle(settings):
    """Toggle the cursor display mode and update the panel label."""
    settings.toggle_cursor_mode()
    update_cursor_toggle_label(settings)


def _on_record_duration_change(value: int, settings, app_state) -> None:
    """Persist a new recording duration selection in settings and runtime state."""
    settings.record_duration = value
    app_state.record_duration = value
    settings.save()


def _on_start_recording(app_state, settings) -> None:
    """Start or stop a recording session from the controls toolbar."""
    if app_state.is_recording or app_state.is_countdown:
        app_state.is_recording = False
        dpg.set_item_label("start_recording_btn", "Start Recording")
        app_state.recording_indicator = False
        app_state.stopwatch_elapsed = 0.0
        return  # Prevent double start
    app_state.is_countdown = True
    app_state.countdown_value = 4
    app_state.record_duration = settings.record_duration
    app_state.record_buffer = []
    app_state.recording_indicator = False
    app_state.stopwatch_elapsed = 0.0
    # change label of start button to "Stop Recording"
    dpg.set_item_label("start_recording_btn", "Stop Recording")


def _build_session_buttons(session_state: dict) -> None:
    """Add session-level panel button: Restart."""
    dpg.add_button(
        label="Restart Session",
        callback=lambda: session_state.update({"action": "restart"}),
        width=PANEL_BTN_W,
        height=PANEL_BTN_H,
    )


def _build_recording_controls(app_state, settings) -> None:
    """Add recording duration and start/stop button to the panel."""
    with dpg.group(horizontal=True):
        dpg.add_text("Duration (s):")
        dpg.add_input_int(
            tag="record_duration_input",
            default_value=int(settings.record_duration),
            min_value=1,
            max_value=120,
            width=PANEL_SLIDER_W - 104,
            callback=lambda s, v: _on_record_duration_change(v, settings, app_state),
        )
    dpg.add_spacer(height=4)
    dpg.add_button(
        tag="start_recording_btn",
        label="Start Recording",
        width=PANEL_BTN_W,
        height=PANEL_BTN_H,
        callback=lambda: _on_start_recording(app_state, settings),
        enabled=not app_state.is_recording and not app_state.is_countdown,
    )


def _build_cursor_controls(app_state, settings) -> None:
    """Add cursor mode toggle, trail, and smoothing filter to the panel."""
    dpg.add_button(
        tag="cursor_toggle_btn",
        label=_cursor_label(settings),
        callback=lambda: _on_cursor_toggle(settings),
        width=PANEL_BTN_W,
        height=PANEL_BTN_H,
    )
    app_state.update_cursor_toggle_label = lambda: update_cursor_toggle_label(settings)
    dpg.add_spacer(height=8)
    dpg.add_text("Sway trail")
    trail_items = ["None", "Medium", "Long"]
    trail_map = {"None": 0, "Medium": 30, "Long": 100}
    trail_rmap = {0: "None", 30: "Medium", 100: "Long"}
    current_label = trail_rmap.get(settings.trail_length, "Long")
    dpg.add_combo(
        tag="trail_combo",
        items=trail_items,
        default_value=current_label,
        width=PANEL_COMBO_W,
        callback=lambda s, v: _on_trail_change(trail_map[v], settings),
    )
    dpg.add_spacer(height=8)
    dpg.add_text("Smoothing filter")
    dpg.add_slider_int(
        tag="filter_slider",
        default_value=settings.filter_window,
        min_value=FILTER_MIN,
        max_value=FILTER_MAX,
        width=PANEL_SLIDER_W,
        format="%d frames",
        callback=lambda s, v: _on_filter_change(v, settings, app_state),
    )


def _build_visualisation_controls(app_state, settings, session_state: dict) -> None:
    """Add zoom controls and clear screen to the panel."""
    dpg.add_text("Zoom")
    dpg.add_slider_float(
        tag="zoom_slider",
        default_value=settings.zoom_factor,
        min_value=ZOOM_MIN,
        max_value=ZOOM_MAX,
        width=PANEL_SLIDER_W,
        format="%.2fx",
        callback=lambda s, v: _on_zoom_change(v, settings, app_state),
    )
    dpg.add_spacer(height=4)
    dpg.add_button(
        label="Fit View to Sway Path",
        tag="zoom_to_bbox_btn",
        callback=lambda: session_state.update({"action": "zoom_to_bbox_and_reset_pan"}),
        width=PANEL_BTN_W,
        height=PANEL_BTN_H,
    )
    dpg.add_spacer(height=8)
    dpg.add_button(
        label="Clear Screen",
        callback=lambda: session_state.update({"action": "clear"}),
        width=PANEL_BTN_W,
        height=PANEL_BTN_H,
    )


def build_panel_controls(app_state, settings, session_state: dict) -> None:
    """Populate the settings panel with all control sections."""
    _build_section_header("SESSION")
    _build_session_buttons(session_state)

    _build_section_header("RECORDING")
    _build_recording_controls(app_state, settings)

    _build_section_header("CURSOR & MOVEMENT")
    _build_cursor_controls(app_state, settings)

    _build_section_header("VISUALISATION")
    _build_visualisation_controls(app_state, settings, session_state)


def _on_trail_change(value: int, settings) -> None:
    """Update the trail length setting used for the historical cursor path."""
    settings.trail_length = value
    settings.save()


def _on_filter_change(value: int, settings, app_state) -> None:
    """Update the moving average filter window and trim the current filter buffer."""
    settings.filter_window = value
    if len(app_state.filter_buffer) > value:
        app_state.filter_buffer = app_state.filter_buffer[-value:]
    settings.save()


def _on_zoom_change(value: float, settings, app_state) -> None:
    """Apply a new zoom factor and immediately rescale runtime extents."""
    value = ZOOM_SCALE**value
    settings.zoom_factor = value
    app_state.zoomed_max_x = app_state.raw_max_x * value
    app_state.zoomed_max_y = app_state.raw_max_y * value
    app_state.zoomed_min_x = app_state.raw_min_x * value
    app_state.zoomed_min_y = app_state.raw_min_y * value
    settings.save()


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

    dpg.draw_rectangle((0, 0), (sw, sh), fill=CALIB_BG_COLOR, color=CALIB_BG_COLOR, parent=dl)

    tag = _wii_texture_tags[2]
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

    _crisp_text((text_x, text_y), "Step", color=(250, 250, 250, 255), size=font_size, parent=dl)
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
        dpg.draw_line((x0, y0), (x1, y1), color=color, thickness=CALIB_ARC_THICKNESS, parent=dl)


def draw_connection_screen(dl, app_state) -> None:
    """Draw the 'Trying to connect' screen."""
    sw, sh = app_state.screen_width, app_state.screen_height
    dpg.draw_rectangle((0, 0), (sw, sh), fill=CALIB_BG_COLOR, color=CALIB_BG_COLOR, parent=dl)
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
    dpg.draw_rectangle((0, 0), (sw, sh), fill=CALIB_BG_COLOR, color=CALIB_BG_COLOR, parent=dl)

    cfg = dpg.get_item_configuration(_connection_texture_tag)
    iw_orig, ih_orig = cfg["width"], cfg["height"]
    scaled_h = int(0.8 * sh)
    scaled_w = int(scaled_h * iw_orig / ih_orig)
    img_x = sw // 2 - scaled_w // 2
    img_y = sh // 2 - scaled_h // 2
    dpg.draw_image(
        _connection_texture_tag, (img_x, img_y), (img_x + scaled_w, img_y + scaled_h), parent=dl
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
        _crisp_text((mx, my + i * font_size * 1.4), text, color=color, size=font_size, parent=dl)


# ---------------------------------------------------------------------------
# Main balance screen
# ---------------------------------------------------------------------------


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

    # Centre lines
    line_w = CANVAS_LINE_W
    dpg.draw_line((0, cy), (sw, cy), color=CANVAS_LINE, thickness=line_w, parent=dl)
    dpg.draw_line((cx, 0), (cx, sh), color=CANVAS_LINE, thickness=line_w, parent=dl)
    dpg.draw_circle(
        (cx, cy), CANVAS_CENTRE_R, color=CANVAS_CENTRE_DOT, fill=CANVAS_CENTRE_DOT, parent=dl
    )

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
        dpg.draw_circle(
            (vx, vy), scaled_radius, color=(0, 200, 255, 180), fill=(0, 200, 255, 60), parent=dl
        )

    # Trail (S2: sliced to trail_length; coords are in viewport space)
    coords = (
        app_state.historical_coords[-settings.trail_length :] if settings.trail_length > 0 else []
    )
    n = len(coords)
    for i in range(1, n):
        frac = i / n
        tc = (
            int(frac * TRAIL_COLOR_BASE[0]),
            int(frac * TRAIL_COLOR_BASE[1]),
            int(frac * TRAIL_COLOR_BASE[2]),
            200,
        )
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
        dpg.draw_circle((ball_x, ball_y), 20, color=CURSOR_COLOR, fill=CURSOR_COLOR, parent=dl)

    # Bounding box — max_x/min_x are relative coordinate extents (not viewport coords).
    # They need to be offset by canvas centre (cx, cy) to get viewport coords.
    dpg.draw_rectangle(
        (cx + min_x, cy + min_y),
        (cx + max_x, cy + max_y),
        color=BBOX_COLOR,
        thickness=BBOX_THICKNESS,
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

    # Draw recording indicator group (timer, dot, REC) anchored to right edge
    if getattr(app_state, "recording_indicator", False):
        right_margin = 20
        dot_radius = 18
        dot_diameter = dot_radius * 2
        spacing = 12
        font_size = 32

        # Stopwatch timer (mm:ss.t)
        elapsed = getattr(app_state, "stopwatch_elapsed", 0.0)
        mins = int(elapsed // 60)
        secs = elapsed % 60
        timer_str = f"{mins:02d}:{secs:04.1f}"

        # Estimate text widths (approximate, since DPG doesn't provide get_text_size)
        timer_width = font_size * 3  # e.g., "00:00.0"
        rec_width = font_size * 2  # e.g., "REC"

        # Recording indicator sits at the top-right of the canvas
        y = 8
        # Compute starting x position for timer (leftmost)
        x_timer = sw - right_margin - (timer_width + spacing + dot_diameter + spacing + rec_width)

        # Draw timer
        _crisp_text((x_timer, y), timer_str, color=(255, 0, 0, 255), size=font_size, parent=dl)

        # Draw dot (centered vertically with text)
        x_dot = x_timer + timer_width + spacing + dot_radius
        y_dot = y + font_size // 2
        dpg.draw_circle(
            (x_dot, y_dot), dot_radius, color=(255, 0, 0, 255), fill=(255, 0, 0, 200), parent=dl
        )

        # Draw "REC"
        x_rec = x_dot + dot_radius + spacing
        _crisp_text((x_rec, y), "REC", color=(255, 0, 0, 255), size=font_size, parent=dl)
