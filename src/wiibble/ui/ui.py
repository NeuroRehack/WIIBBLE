# ui.py
# All rendering via Dear PyGui drawlist API.
# The viewport_drawlist draws directly onto the viewport background — no
# window chrome around the canvas. UI controls sit in a separate overlay window.

import math
import time
from pathlib import Path

import dearpygui.dearpygui as dpg

import wiibble.ui.theme as _theme_module
from wiibble.features.data_processing import logical_to_viewport
from wiibble.session_actions import (
    apply_board_cal_reference,
    apply_body_weight,
    apply_cursor_size,
    apply_filter_window,
    apply_flip_horizontal,
    apply_flip_vertical,
    apply_record_duration,
    apply_recording_dir,
    apply_recording_prefix,
    apply_setting_bool,
    apply_target_dwell_seconds,
    apply_trail_length,
    apply_zoom_slider,
    request_calibrate_board,
    request_calibrate_scale,
    toggle_cursor_mode,
    toggle_recording,
)
from wiibble.session_report.launcher import open_report_in_browser
from wiibble.utils.recording_names import report_search_paths
from wiibble.ui.theme import (
    BAR_GREY_COLOR,
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
    ICON_FLIP_HORIZONTAL,
    ICON_FLIP_VERTICAL,
    ICON_INFINITY,
    STATS_TEXT_COLOR,
    TRAIL_COLOR_BASE,
    bind_text_font,
    get_stats_bar_color,
)
from wiibble.utils.constants import (
    BOARD_CAL_REFERENCE_MAX,
    BOARD_CAL_REFERENCE_MIN,
    BODY_WEIGHT_MAX,
    BODY_WEIGHT_MIN,
    CURSOR_SIZE_MAX,
    CURSOR_SIZE_MIN,
    FILTER_MAX,
    FILTER_MIN,
    PANEL_BTN_H,
    PANEL_BTN_W,
    PANEL_SECTION_SPACING,
    PANEL_SLIDER_W,
    PANEL_TOGGLE_BTN_SIZE,
    PANEL_W,
    QUICK_ACCESS_GAP,
    QUICK_ACCESS_MARGIN,
    QUICK_ACCESS_WINDOW_PAD,
    RECORDING_INDICATOR_DOT_RADIUS,
    RECORDING_INDICATOR_LIMIT_FONT_SIZE,
    RECORDING_INDICATOR_RIGHT_MARGIN,
    RECORDING_INDICATOR_SPACING,
    RECORDING_INDICATOR_TIMER_FONT_SIZE,
    RECORDING_INDICATOR_TIMER_GAP,
    RECORDING_INDICATOR_Y,
    TARGET_DWELL_MAX,
    TARGET_DWELL_MIN,
    TARGET_DWELL_STEP,
    ZOOM_MAX,
    ZOOM_MIN,
)
from wiibble.utils.recording_names import (
    DEFAULT_RECORDING_DIR,
    normalize_recording_prefix,
)
from wiibble.utils.resources import CONNECTION_PATH, IMAGE_PATHS, PERSON_IMAGE_PATH

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


def _crisp_icon_text(pos, text: str, color: tuple, size: int, parent) -> int:
    """Like _crisp_text but binds the 100px FontAwesome atlas for icon glyphs."""
    tag = dpg.draw_text(pos, text, color=color, size=size, parent=parent)
    if _theme_module.FA_ICON_FONT_DRAW is not None and dpg.does_item_exist(tag):
        dpg.bind_item_font(tag, _theme_module.FA_ICON_FONT_DRAW)
    elif _theme_module.FA_ICON_FONT is not None and dpg.does_item_exist(tag):
        dpg.bind_item_font(tag, _theme_module.FA_ICON_FONT)
    return tag


def _measure_crisp_text_width(text: str, size: int) -> float:
    """Measure draw_text width using the loaded crisp font atlas (100px → size)."""
    if _theme_module.TEXT_FONT is not None:
        try:
            w, _ = dpg.get_text_size(text, font=_theme_module.TEXT_FONT)
            return w * (size / 100.0)
        except Exception:
            pass
    # Fallback before first frame or if font missing (~0.55 em per char for digits).
    return len(text) * size * 0.55


def _estimate_text_width(text: str, font_size: int) -> int:
    """Approximate pixel width for draw_text labels."""
    return int(_measure_crisp_text_width(text, font_size))


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
        dpg.add_viewport_drawlist(tag="stats_dl", front=False)
    dpg.delete_item("stats_dl", children_only=True)
    _stats_cache["left"] = -1
    _stats_cache["weight"] = -1
    _stats_cache["right"] = -1


def set_stats_bar_visible(visible: bool) -> None:
    """Show or hide the bottom stats overlay (e.g. during calibration screens)."""
    if not dpg.does_item_exist("stats_dl"):
        return
    dpg.configure_item("stats_dl", show=visible)
    if not visible:
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
        (0, bar_top),
        (sw, bar_bot),
        fill=BAR_GREY_COLOR,
        color=BAR_GREY_COLOR,
        parent="stats_dl",
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
        (x0, bar_top),
        (sw // 2, bar_bot),
        fill=bar_color,
        color=bar_color,
        parent="stats_dl",
    )
    x0 = sw // 2
    x1 = sw // 2 + pr * sw // 2
    dpg.draw_rectangle(
        (x0, bar_top), (x1, bar_bot), fill=bar_color, color=bar_color, parent="stats_dl"
    )

    t = dpg.draw_text(
        (10, y),
        f"{left_val}%",
        color=STATS_TEXT_COLOR,
        size=font_size,
        parent="stats_dl",
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
        no_scrollbar=True,
        no_collapse=True,
        no_scroll_with_mouse=True,
        pos=(0, 0),
        width=PANEL_W,
        height=screen_height,
        show=False,
    ):
        # Fixed header row
        with dpg.group(horizontal=True):
            dpg.add_button(
                tag="panel_close_btn",
                label=toggle_label,
                callback=toggle_callback,
                width=PANEL_TOGGLE_BTN_SIZE,
                height=PANEL_TOGGLE_BTN_SIZE,
            )
            dpg.add_spacer(width=8)
            dpg.add_text("Settings")
        dpg.add_separator()
        dpg.add_spacer(height=PANEL_SECTION_SPACING)
        # Scrollable area for settings controls only
        header_height = (
            128  # buffer enough for header, separator, spacing and window padding
        )
        controls_height = max(40, screen_height - header_height)
        with dpg.child_window(
            tag="settings_scroll",
            width=PANEL_W - 10,
            autosize_x=False,
            autosize_y=False,
            height=controls_height,
            no_scrollbar=False,
            horizontal_scrollbar=False,
            border=False,
            no_scroll_with_mouse=False,
            always_use_window_padding=False,
            frame_style=False,
        ):
            settings_group_builder()
            dpg.add_spacer(height=24)

    if _theme_module.FA_ICON_FONT is not None:
        dpg.bind_item_font("panel_close_btn", _theme_module.FA_ICON_FONT)


def _left_quick_access_window_size(num_buttons: int) -> tuple[int, int]:
    """Return (width, height) for the quick-access window holding num_buttons."""
    btn = PANEL_TOGGLE_BTN_SIZE
    gap = QUICK_ACCESS_GAP
    content_w = num_buttons * btn + max(0, num_buttons - 1) * gap
    return content_w + QUICK_ACCESS_WINDOW_PAD, btn + QUICK_ACCESS_WINDOW_PAD // 2 + 4


def build_left_quick_access(
    gear_label: str, toggle_callback, session_state: dict
) -> None:
    """Create the top-left quick-access bar (gear + clear screen + reset counter)."""
    if dpg.does_item_exist("left_quick_access_window"):
        dpg.delete_item("left_quick_access_window")

    clear_label = (
        _theme_module.ICON_ERASER if _theme_module.FA_ICON_FONT is not None else "Clr"
    )
    reset_label = (
        _theme_module.ICON_COUNTER_RESET
        if _theme_module.FA_ICON_FONT is not None
        else "Rst"
    )
    btn = PANEL_TOGGLE_BTN_SIZE
    margin = QUICK_ACCESS_MARGIN
    window_w, window_h = _left_quick_access_window_size(3)

    with (
        dpg.window(
            tag="left_quick_access_window",
            no_title_bar=True,
            no_resize=True,
            no_move=True,
            no_scrollbar=True,
            no_collapse=True,
            no_background=True,
            pos=(margin, margin),
            width=window_w,
            height=window_h,
            show=False,
        ),
        dpg.group(horizontal=True),
    ):
        dpg.add_button(
            tag="panel_float_btn",
            label=gear_label,
            callback=toggle_callback,
            width=btn,
            height=btn,
        )
        dpg.add_button(
            tag="clear_screen_quick_btn",
            label=clear_label,
            callback=lambda: session_state.update({"action": "clear"}),
            width=btn,
            height=btn,
        )
        reset_btn = dpg.add_button(
            tag="reset_counter_quick_btn",
            label=reset_label,
            callback=lambda: session_state.update({"action": "reset_target_counter"}),
            width=btn,
            height=btn,
        )
        if _theme_module.FA_ICON_FONT is not None:
            dpg.bind_item_font(reset_btn, _theme_module.FA_ICON_FONT)

    with dpg.tooltip(parent="reset_counter_quick_btn"):
        dpg.add_text("Reset the target hit counter to zero.")

    if _theme_module.FA_ICON_FONT is not None:
        dpg.bind_item_font("panel_float_btn", _theme_module.FA_ICON_FONT)
        dpg.bind_item_font("clear_screen_quick_btn", _theme_module.FA_ICON_FONT)

    with dpg.tooltip(parent="clear_screen_quick_btn"):
        dpg.add_text(
            "Clear Screen — remove targets and sway trail.\nShortcut: Ctrl+Shift+C"
        )


def build_recording_quick_btn(app_state, settings) -> None:
    """Create the top-right recording toggle quick-access button."""
    if dpg.does_item_exist("recording_quick_window"):
        dpg.delete_item("recording_quick_window")

    btn = RECORDING_INDICATOR_DOT_RADIUS * 2
    vw = dpg.get_viewport_width()
    layout = _recording_indicator_layout(vw, settings.record_duration)
    x = int(layout["dot_cx"] - layout["dot_radius"])
    y = int(layout["dot_cy"] - layout["dot_radius"])

    with dpg.window(
        tag="recording_quick_window",
        no_title_bar=True,
        no_resize=True,
        no_move=True,
        no_scrollbar=True,
        no_collapse=True,
        no_background=True,
        pos=(x, y),
        width=btn + 4,
        height=btn + 4,
        show=False,
    ):
        dpg.add_button(
            tag="recording_quick_btn",
            label="",
            callback=lambda: _on_start_recording(app_state, settings),
            width=btn,
            height=btn,
        )

    dpg.bind_item_theme("recording_quick_btn", _get_recording_quick_idle_theme())

    with dpg.tooltip(parent="recording_quick_btn"):
        dpg.add_text("Start / Stop Recording.\nShortcut: Ctrl+Space")


def update_left_quick_access_layout(
    toolbar_visible: bool, toolbar_enabled: bool
) -> None:
    """Reposition and show/hide left quick-access buttons based on panel state."""
    if not dpg.does_item_exist("left_quick_access_window"):
        return

    margin = QUICK_ACCESS_MARGIN

    if toolbar_visible:
        dpg.configure_item("panel_float_btn", show=False)
        dpg.configure_item("clear_screen_quick_btn", show=True)
        dpg.configure_item("reset_counter_quick_btn", show=True)
        dpg.set_item_pos("left_quick_access_window", (PANEL_W + 8, margin))
        window_w, window_h = _left_quick_access_window_size(2)
    else:
        dpg.configure_item("panel_float_btn", show=True)
        dpg.configure_item("clear_screen_quick_btn", show=True)
        dpg.configure_item("reset_counter_quick_btn", show=True)
        dpg.set_item_pos("left_quick_access_window", (margin, margin))
        window_w, window_h = _left_quick_access_window_size(3)

    dpg.configure_item(
        "left_quick_access_window",
        width=window_w,
        height=window_h,
        show=toolbar_enabled,
    )


def update_recording_quick_access_position(
    viewport_width: int, limit_seconds: int | float = 0
) -> None:
    """Anchor the recording quick-access button over the recording-indicator dot."""
    if not dpg.does_item_exist("recording_quick_window"):
        return
    layout = _recording_indicator_layout(viewport_width, limit_seconds)
    btn = layout["dot_radius"] * 2
    x = int(layout["dot_cx"] - layout["dot_radius"])
    y = int(layout["dot_cy"] - layout["dot_radius"])
    dpg.set_item_pos("recording_quick_window", (x, y))
    dpg.configure_item("recording_quick_window", width=btn + 4, height=btn + 4)
    if dpg.does_item_exist("recording_quick_btn"):
        dpg.configure_item("recording_quick_btn", width=btn, height=btn)


def set_quick_access_visible(visible: bool, session_state: dict) -> None:
    """Show or hide all canvas quick-access controls."""
    toolbar_visible = session_state.get("toolbar_visible", False)
    toolbar_enabled = session_state.get("toolbar_enabled", False)
    if visible:
        update_left_quick_access_layout(toolbar_visible, toolbar_enabled)
        if dpg.does_item_exist("recording_quick_window"):
            dpg.configure_item("recording_quick_window", show=toolbar_enabled)
    else:
        if dpg.does_item_exist("left_quick_access_window"):
            dpg.configure_item("left_quick_access_window", show=False)
        if dpg.does_item_exist("recording_quick_window"):
            dpg.configure_item("recording_quick_window", show=False)


def is_mouse_over_quick_access() -> bool:
    """Return True if the mouse is over a quick-access button."""
    for tag in (
        "panel_float_btn",
        "clear_screen_quick_btn",
        "reset_counter_quick_btn",
        "recording_quick_btn",
    ):
        if (
            dpg.does_item_exist(tag)
            and dpg.is_item_shown(tag)
            and dpg.is_item_hovered(tag)
        ):
            return True
    return False


def collapse_settings_panel(session_state: dict) -> bool:
    """Hide the settings panel when it is open. Returns True if it was collapsed."""
    if not session_state.get("toolbar_visible", False):
        return False
    session_state["toolbar_visible"] = False
    if dpg.does_item_exist("control_panel"):
        dpg.configure_item("control_panel", show=False)
    update_left_quick_access_layout(
        False,
        session_state.get("toolbar_enabled", False),
    )
    session_state["action"] = "toolbar_toggled"
    return True


def show_settings_panel(session_state: dict) -> None:
    """Show the settings panel."""
    session_state["toolbar_visible"] = True
    if dpg.does_item_exist("control_panel"):
        dpg.configure_item("control_panel", show=True)
    update_left_quick_access_layout(
        True,
        session_state.get("toolbar_enabled", False),
    )
    session_state["action"] = "toolbar_toggled"


# ---------------------------------------------------------------------------
# Per-widget theme caches — created lazily on first use
# ---------------------------------------------------------------------------
_trail_active_theme = None
_recording_active_theme = None
_recording_quick_idle_theme = None
_recording_quick_active_theme = None


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


def _get_recording_quick_idle_theme():
    """Round red record button shown when idle."""
    global _recording_quick_idle_theme
    radius = RECORDING_INDICATOR_DOT_RADIUS
    if _recording_quick_idle_theme is None or not dpg.does_item_exist(
        _recording_quick_idle_theme
    ):
        with dpg.theme() as t, dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(
                dpg.mvThemeCol_Button,
                (220, 40, 40, 255),
                category=dpg.mvThemeCat_Core,
            )
            dpg.add_theme_color(
                dpg.mvThemeCol_ButtonHovered,
                (240, 60, 60, 255),
                category=dpg.mvThemeCat_Core,
            )
            dpg.add_theme_color(
                dpg.mvThemeCol_ButtonActive,
                (255, 80, 80, 255),
                category=dpg.mvThemeCat_Core,
            )
            dpg.add_theme_style(
                dpg.mvStyleVar_FrameRounding, radius, category=dpg.mvThemeCat_Core
            )
        _recording_quick_idle_theme = t
    return _recording_quick_idle_theme


def _get_recording_quick_active_theme():
    """Square red stop button shown while recording or during countdown."""
    global _recording_quick_active_theme
    if _recording_quick_active_theme is None or not dpg.does_item_exist(
        _recording_quick_active_theme
    ):
        with dpg.theme() as t, dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(
                dpg.mvThemeCol_Button,
                (180, 50, 50, 255),
                category=dpg.mvThemeCat_Core,
            )
            dpg.add_theme_color(
                dpg.mvThemeCol_ButtonHovered,
                (200, 70, 70, 255),
                category=dpg.mvThemeCat_Core,
            )
            dpg.add_theme_color(
                dpg.mvThemeCol_ButtonActive,
                (220, 90, 90, 255),
                category=dpg.mvThemeCat_Core,
            )
            dpg.add_theme_style(
                dpg.mvStyleVar_FrameRounding, 0, category=dpg.mvThemeCat_Core
            )
        _recording_quick_active_theme = t
    return _recording_quick_active_theme


def _get_trail_active_theme():
    """Return (creating on demand) the highlighted theme for the active trail button."""
    global _trail_active_theme
    if _trail_active_theme is None or not dpg.does_item_exist(_trail_active_theme):
        with dpg.theme() as t, dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(
                dpg.mvThemeCol_Button,
                _theme_module.C_BRAND,
                category=dpg.mvThemeCat_Core,
            )
            dpg.add_theme_color(
                dpg.mvThemeCol_ButtonHovered,
                _theme_module.C_BTN_ACTIVE,
                category=dpg.mvThemeCat_Core,
            )
            dpg.add_theme_color(
                dpg.mvThemeCol_ButtonActive,
                _theme_module.C_BTN_ACTIVE,
                category=dpg.mvThemeCat_Core,
            )
        _trail_active_theme = t
    return _trail_active_theme


def _get_recording_theme():
    """Return (creating on demand) a red theme for the Stop Recording button."""
    global _recording_active_theme
    if _recording_active_theme is None or not dpg.does_item_exist(
        _recording_active_theme
    ):
        with dpg.theme() as t, dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(
                dpg.mvThemeCol_Button,
                (180, 50, 50, 255),
                category=dpg.mvThemeCat_Core,
            )
            dpg.add_theme_color(
                dpg.mvThemeCol_ButtonHovered,
                (200, 70, 70, 255),
                category=dpg.mvThemeCat_Core,
            )
            dpg.add_theme_color(
                dpg.mvThemeCol_ButtonActive,
                (220, 90, 90, 255),
                category=dpg.mvThemeCat_Core,
            )
        _recording_active_theme = t
    return _recording_active_theme


def sync_recording_buttons(*, recording_active: bool) -> None:
    """Keep panel and quick-access recording buttons in sync."""
    panel_label = "Stop Recording" if recording_active else "Start Recording"
    panel_theme = _get_recording_theme() if recording_active else 0
    if dpg.does_item_exist("start_recording_btn"):
        dpg.set_item_label("start_recording_btn", panel_label)
        dpg.bind_item_theme("start_recording_btn", panel_theme)

    if dpg.does_item_exist("recording_quick_btn"):
        dpg.set_item_label("recording_quick_btn", "")
        dpg.bind_item_theme(
            "recording_quick_btn",
            _get_recording_quick_active_theme()
            if recording_active
            else _get_recording_quick_idle_theme(),
        )


def _update_trail_buttons(active_label: str) -> None:
    """Highlight the active trail selection button; clear highlight on the others."""
    for lbl in ("None", "Medium", "Long"):
        tag = f"trail_btn_{lbl.lower()}"
        if dpg.does_item_exist(tag):
            if lbl == active_label:
                dpg.bind_item_theme(tag, _get_trail_active_theme())
            else:
                dpg.bind_item_theme(tag, 0)


def _update_flip_buttons(settings) -> None:
    """Highlight flip-axis toggle buttons when their setting is active."""
    for tag, active in (
        ("flip_vertical_btn", settings.flip_vertical),
        ("flip_horizontal_btn", settings.flip_horizontal),
    ):
        if dpg.does_item_exist(tag):
            if active:
                dpg.bind_item_theme(tag, _get_trail_active_theme())
            else:
                dpg.bind_item_theme(tag, 0)


def _build_section_header(label: str, accent_color=None) -> None:
    """Render a section label with accent bar and separator line."""
    dpg.add_spacer(height=PANEL_SECTION_SPACING)
    with dpg.group(horizontal=True):
        if accent_color is not None:
            accent_item = dpg.add_button(label="", width=4, height=18)
            with dpg.theme() as _accent_theme:
                with dpg.theme_component(dpg.mvButton):
                    dpg.add_theme_color(
                        dpg.mvThemeCol_Button,
                        accent_color,
                        category=dpg.mvThemeCat_Core,
                    )
                    dpg.add_theme_color(
                        dpg.mvThemeCol_ButtonHovered,
                        accent_color,
                        category=dpg.mvThemeCat_Core,
                    )
                    dpg.add_theme_color(
                        dpg.mvThemeCol_ButtonActive,
                        accent_color,
                        category=dpg.mvThemeCat_Core,
                    )
            dpg.bind_item_theme(accent_item, _accent_theme)
            dpg.add_spacer(width=4)
        t = dpg.add_text(label)
        # Apply dim text colour to section headings
        with dpg.theme() as _section_theme, dpg.theme_component(dpg.mvText):
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
    return (
        "Switch to Avatar" if settings.cursor_mode == "circle" else "Switch to Circle"
    )


def update_cursor_toggle_label(settings):
    """Update the panel cursor button label to reflect the current mode."""
    dpg.set_item_label("cursor_toggle_btn", _cursor_label(settings))


def _on_cursor_toggle(settings):
    """Toggle the cursor display mode and update the panel label."""
    toggle_cursor_mode(settings)
    update_cursor_toggle_label(settings)


def _on_cursor_size_change(value: int, settings) -> None:
    """Persist a new cursor size selection and update settings."""
    apply_cursor_size(settings, value)


def _on_record_duration_change(value: int, settings, app_state) -> None:
    """Persist a new recording duration selection in settings and runtime state."""
    apply_record_duration(settings, app_state, value)
    update_recording_quick_access_position(dpg.get_viewport_width(), value)


def _on_start_recording(app_state, settings) -> None:
    """Start or stop a recording session from the controls toolbar."""
    active = toggle_recording(app_state, settings)
    sync_recording_buttons(recording_active=active)


def _on_body_weight_change(value: float, settings, app_state) -> None:
    """Persist a manual body weight and sync it to runtime state."""
    clamped = apply_body_weight(settings, app_state, value)
    if clamped is not None and dpg.does_item_exist("body_weight_input"):
        dpg.set_value("body_weight_input", clamped)


def _on_calibrate_board(session_state: dict) -> None:
    """Request on-board weight calibration from the main loop."""
    request_calibrate_board(session_state)


def _on_board_cal_reference_change(value: float, settings) -> None:
    """Persist the reference mass used for board scale calibration."""
    clamped = apply_board_cal_reference(settings, value)
    if clamped is not None and dpg.does_item_exist("board_cal_reference_input"):
        dpg.set_value("board_cal_reference_input", clamped)


def _on_calibrate_scale(session_state: dict) -> None:
    """Request board scale-factor calibration from the main loop."""
    request_calibrate_scale(session_state)


def update_scale_factor_label(settings) -> None:
    """Refresh the read-only scale factor display in the calibration panel."""
    if dpg.does_item_exist("scale_factor_label"):
        dpg.set_value(
            "scale_factor_label", f"Scale factor: {settings.scale_factor:.4f}"
        )


def _build_calibration_controls(app_state, settings, session_state: dict) -> None:
    """Add body weight and board scale calibration controls to the panel."""
    dpg.add_text("Body weight (kg)")
    input_w = 180
    btn_w = PANEL_BTN_W - input_w - 4
    with dpg.group(horizontal=True):
        dpg.add_input_float(
            tag="body_weight_input",
            default_value=settings.body_weight_kg,
            min_value=BODY_WEIGHT_MIN,
            max_value=BODY_WEIGHT_MAX,
            format="%.1f",
            width=input_w,
            callback=lambda s, v: _on_body_weight_change(v, settings, app_state),
        )
        dpg.add_button(
            tag="calibrate_board_btn",
            label="Auto",
            width=btn_w,
            height=PANEL_BTN_H,
            callback=lambda: _on_calibrate_board(session_state),
        )
    with dpg.tooltip(parent="body_weight_input"):
        dpg.add_text(
            "Patient body weight for cursor normalization and recordings.\n"
            "Default is 70 kg if not set."
        )
    with dpg.tooltip(parent="calibrate_board_btn"):
        dpg.add_text(
            "Run step-off / step-on calibration to measure weight on the board.\n"
            "Updates this field when complete."
        )
    dpg.add_spacer(height=8)
    dpg.add_text("Board reference (kg)")
    with dpg.group(horizontal=True):
        dpg.add_input_float(
            tag="board_cal_reference_input",
            default_value=settings.board_cal_reference_kg,
            min_value=BOARD_CAL_REFERENCE_MIN,
            max_value=BOARD_CAL_REFERENCE_MAX,
            format="%.1f",
            width=input_w,
            callback=lambda s, v: _on_board_cal_reference_change(v, settings),
        )
        dpg.add_button(
            tag="calibrate_scale_btn",
            label="Cal scale",
            width=btn_w,
            height=PANEL_BTN_H,
            callback=lambda: _on_calibrate_scale(session_state),
        )
    with dpg.tooltip(parent="board_cal_reference_input"):
        dpg.add_text(
            "Known mass placed on the board for hardware scale calibration.\n"
            "Use a certified weight between 10 and 150 kg."
        )
    with dpg.tooltip(parent="calibrate_scale_btn"):
        dpg.add_text(
            "Tare the board, place the reference mass, and compute\n"
            "the HID raw-to-kg scale factor for this board."
        )
    dpg.add_spacer(height=4)
    dpg.add_text(
        f"Scale factor: {settings.scale_factor:.4f}",
        tag="scale_factor_label",
        wrap=PANEL_BTN_W,
    )


def _on_recording_prefix_change(value: str, settings) -> None:
    """Persist a custom recording filename prefix."""
    normalized = apply_recording_prefix(settings, value)
    if (
        dpg.does_item_exist("recording_prefix_input")
        and dpg.get_value("recording_prefix_input") != normalized
    ):
        dpg.set_value("recording_prefix_input", normalized)


def _open_recording_dir_picker(settings) -> None:
    """Open the Dear PyGui file dialog in directory mode (light theme override)."""
    default_dir = str(DEFAULT_RECORDING_DIR)
    initial = settings.recording_dir or default_dir

    # Create a more detailed light theme for the dialog if not already present
    if not dpg.does_item_exist("recording_dir_dialog_theme"):
        with dpg.theme(tag="recording_dir_dialog_theme"):
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(
                    dpg.mvThemeCol_WindowBg,
                    (245, 245, 245, 255),
                    category=dpg.mvThemeCat_Core,
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_ChildBg,
                    (255, 255, 255, 255),
                    category=dpg.mvThemeCat_Core,
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_Text, (20, 20, 20, 255), category=dpg.mvThemeCat_Core
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_Button,
                    (220, 220, 220, 255),
                    category=dpg.mvThemeCat_Core,
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_ButtonHovered,
                    (200, 200, 200, 255),
                    category=dpg.mvThemeCat_Core,
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_ButtonActive,
                    (180, 180, 180, 255),
                    category=dpg.mvThemeCat_Core,
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_FrameBg,
                    (235, 235, 235, 255),
                    category=dpg.mvThemeCat_Core,
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_FrameBgHovered,
                    (220, 220, 220, 255),
                    category=dpg.mvThemeCat_Core,
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_FrameBgActive,
                    (200, 200, 200, 255),
                    category=dpg.mvThemeCat_Core,
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_SliderGrab,
                    (107, 143, 168, 255),
                    category=dpg.mvThemeCat_Core,
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_SliderGrabActive,
                    (180, 180, 180, 255),
                    category=dpg.mvThemeCat_Core,
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_Header,
                    (220, 220, 220, 255),
                    category=dpg.mvThemeCat_Core,
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_HeaderHovered,
                    (200, 200, 200, 255),
                    category=dpg.mvThemeCat_Core,
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_HeaderActive,
                    (180, 180, 180, 255),
                    category=dpg.mvThemeCat_Core,
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_Border,
                    (180, 180, 180, 255),
                    category=dpg.mvThemeCat_Core,
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_ScrollbarBg,
                    (235, 235, 235, 240),
                    category=dpg.mvThemeCat_Core,
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_ScrollbarGrab,
                    (190, 220, 235, 255),
                    category=dpg.mvThemeCat_Core,
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_ScrollbarGrabHovered,
                    (215, 235, 245, 255),
                    category=dpg.mvThemeCat_Core,
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_ScrollbarGrabActive,
                    (240, 255, 255, 255),
                    category=dpg.mvThemeCat_Core,
                )
                # Brighter header and menu bar for dialog
                dpg.add_theme_color(
                    dpg.mvThemeCol_TitleBg,
                    (250, 250, 250, 255),
                    category=dpg.mvThemeCat_Core,
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_TitleBgActive,
                    (245, 245, 245, 255),
                    category=dpg.mvThemeCat_Core,
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_TitleBgCollapsed,
                    (250, 250, 250, 255),
                    category=dpg.mvThemeCat_Core,
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_MenuBarBg,
                    (245, 245, 245, 255),
                    category=dpg.mvThemeCat_Core,
                )
                dpg.add_theme_style(
                    dpg.mvStyleVar_ScrollbarSize, 16, category=dpg.mvThemeCat_Core
                )
                # Light colors for file dialog column header row
                dpg.add_theme_color(
                    dpg.mvThemeCol_Header,
                    (252, 252, 252, 255),
                    category=dpg.mvThemeCat_Core,
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_HeaderHovered,
                    (240, 240, 240, 255),
                    category=dpg.mvThemeCat_Core,
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_HeaderActive,
                    (230, 230, 230, 255),
                    category=dpg.mvThemeCat_Core,
                )

    if not dpg.does_item_exist("recording_dir_dialog"):

        def _on_dir_picker(sender, app_data):
            chosen = app_data.get("file_path_name")
            if chosen:
                apply_recording_dir(settings, chosen)
                if dpg.does_item_exist("recording_dir_label"):
                    dpg.set_value("recording_dir_label", chosen)

        dpg.add_file_dialog(
            directory_selector=True,
            show=False,
            tag="recording_dir_dialog",
            width=700,  # wider for more margin
            height=400,
            default_path=initial,
            callback=_on_dir_picker,
            cancel_callback=lambda s, a: dpg.hide_item("recording_dir_dialog"),
            modal=True,
        )
        dpg.bind_item_theme("recording_dir_dialog", "recording_dir_dialog_theme")
    dpg.show_item("recording_dir_dialog")


# Duration preset values (seconds); 0 = indefinite
_DURATION_PRESETS = [
    (10, "10s"),
    (20, "20s"),
    (30, "30s"),
    (60, "60s"),
    (0, ICON_INFINITY),
]


def _update_duration_preset_buttons(active_val: int) -> None:
    """Highlight the active duration preset button; clear the others."""
    for val, _lbl in _DURATION_PRESETS:
        tag = f"dur_preset_{val}"
        if dpg.does_item_exist(tag):
            if val == active_val:
                dpg.bind_item_theme(tag, _get_trail_active_theme())
            else:
                dpg.bind_item_theme(tag, 0)


def _on_duration_preset_change(val: int, settings, app_state) -> None:
    """Apply a duration preset and sync the manual input."""
    _on_record_duration_change(val, settings, app_state)
    _update_duration_preset_buttons(val)
    if dpg.does_item_exist("record_duration_input"):
        dpg.set_value("record_duration_input", val)


def _on_manual_duration_change(val: int, settings, app_state) -> None:
    """Apply a manually typed duration; clear preset unless it matches."""
    _on_record_duration_change(val, settings, app_state)
    preset_vals = {p[0] for p in _DURATION_PRESETS}
    _update_duration_preset_buttons(val if val in preset_vals else -1)


def _sync_open_report_browser_checkbox(settings) -> None:
    """Enable browser checkbox only when auto-report is on."""
    if dpg.does_item_exist("open_report_in_browser_cb"):
        dpg.configure_item(
            "open_report_in_browser_cb",
            enabled=settings.auto_report_after_recording,
        )


def _on_auto_report_after_recording_change(value: bool, settings) -> None:
    apply_setting_bool(settings, "auto_report_after_recording", value)
    _sync_open_report_browser_checkbox(settings)


def _on_open_report_in_browser_change(value: bool, settings) -> None:
    apply_setting_bool(settings, "open_report_in_browser", value)


def _resolve_last_report_path(app_state) -> Path | None:
    """Return the most recent session report path, if one exists on disk."""
    stored = getattr(app_state, "last_report_path", "")
    if stored:
        path = Path(stored)
        if path.is_file():
            return path

    csv_path = getattr(app_state, "last_recording_csv_path", "")
    if csv_path:
        for candidate in report_search_paths(csv_path):
            if candidate.is_file():
                return candidate
    return None


def _on_view_last_report(app_state) -> None:
    """Re-open the most recent session report in the default browser."""
    report_path = _resolve_last_report_path(app_state)
    if report_path is not None:
        app_state.last_report_path = str(report_path)
        open_report_in_browser(report_path)
        return

    app_state.toast_message = (
        "No report available yet — finish a recording with auto-report enabled"
    )
    app_state.toast_until = time.time() + 4.0


def _build_recording_controls(app_state, settings) -> None:
    """Add recording duration presets, manual input, and start/stop button."""
    dpg.add_text("Duration (s)")
    # 5 preset buttons sharing PANEL_BTN_W; 4 gaps of 4 px between them
    _btn_w = (PANEL_BTN_W - 16) // 5
    with dpg.group(horizontal=True):
        for val, lbl in _DURATION_PRESETS:
            tag = f"dur_preset_{val}"
            b = dpg.add_button(
                tag=tag,
                label=lbl,
                width=_btn_w,
                height=PANEL_BTN_H,
                callback=lambda s, a, u: _on_duration_preset_change(
                    u, settings, app_state
                ),
                user_data=val,
            )
            tip = "Record indefinitely" if val == 0 else f"Record for {val} seconds"
            with dpg.tooltip(parent=tag):
                dpg.add_text(tip)
            # Use small FA font for the ∞ glyph button
            if val == 0 and _theme_module.FA_ICON_FONT_SMALL is not None:
                dpg.bind_item_font(b, _theme_module.FA_ICON_FONT_SMALL)
    dpg.add_spacer(height=4)
    dpg.add_input_int(
        tag="record_duration_input",
        default_value=int(settings.record_duration),
        min_value=0,
        max_value=3600,
        width=PANEL_BTN_W,
        callback=lambda s, v: _on_manual_duration_change(v, settings, app_state),
    )
    with dpg.tooltip(parent="record_duration_input"):
        dpg.add_text(
            "Custom duration in seconds (0 = record indefinitely).\n"
            "Or use the preset buttons above."
        )
    _update_duration_preset_buttons(int(settings.record_duration))
    dpg.add_spacer(height=4)
    dpg.add_button(
        tag="start_recording_btn",
        label="Start Recording",
        width=PANEL_BTN_W,
        height=PANEL_BTN_H,
        callback=lambda: _on_start_recording(app_state, settings),
        enabled=not app_state.is_recording and not app_state.is_countdown,
    )
    with dpg.tooltip(parent="start_recording_btn"):
        dpg.add_text(
            "Begin recording after a 3-second countdown.\nClick again to stop."
        )
    dpg.add_spacer(height=8)
    # Save location
    dpg.add_text("Save location")
    _default_dir = str(DEFAULT_RECORDING_DIR)
    _display_dir = settings.recording_dir if settings.recording_dir else _default_dir
    dpg.add_text(_display_dir, tag="recording_dir_label", wrap=PANEL_BTN_W)
    dpg.add_spacer(height=4)
    dpg.add_button(
        tag="recording_dir_btn",
        label="Choose Folder...",
        width=PANEL_BTN_W,
        height=PANEL_BTN_H,
        callback=lambda: _open_recording_dir_picker(settings),
    )
    with dpg.tooltip(parent="recording_dir_btn"):
        dpg.add_text("Choose the folder where recordings are saved.")
    dpg.add_spacer(height=8)
    dpg.add_text("Prefix")
    dpg.add_input_text(
        tag="recording_prefix_input",
        default_value=normalize_recording_prefix(settings.recording_prefix),
        width=PANEL_BTN_W,
        callback=lambda s, v: _on_recording_prefix_change(v, settings),
    )
    with dpg.tooltip(parent="recording_prefix_input"):
        dpg.add_text(
            "Filename prefix for recordings, metrics JSON, and reports (max 40 characters).\n"
            "Letters, digits, underscores, and hyphens only.\n"
            "Spaces become underscores; other special characters are removed.\n"
            "Leave blank for the default (recording).\n"
            "Example: SPI001_SitStand → SPI001_SitStand_261101174543.csv,\n"
            "features_SPI001_SitStand_261101174543.json,\n"
            "report_SPI001_SitStand_261101174543.html"
        )
    dpg.add_spacer(height=8)
    dpg.add_text("Session report")
    dpg.add_checkbox(
        tag="auto_report_after_recording_cb",
        label="generate report after recording",
        default_value=settings.auto_report_after_recording,
        callback=lambda s, v: _on_auto_report_after_recording_change(v, settings),
    )
    with dpg.tooltip(parent="auto_report_after_recording_cb"):
        dpg.add_text(
            "Generate an HTML posturographic report when a recording ends.\n"
            "Full metrics require at least 20 seconds of data."
        )
    dpg.add_checkbox(
        tag="open_report_in_browser_cb",
        label="Open in browser",
        default_value=settings.open_report_in_browser,
        callback=lambda s, v: _on_open_report_in_browser_change(v, settings),
    )
    with dpg.tooltip(parent="open_report_in_browser_cb"):
        dpg.add_text("Open the report in your default web browser when ready.")
    _sync_open_report_browser_checkbox(settings)
    dpg.add_spacer(height=4)
    dpg.add_button(
        tag="view_last_report_btn",
        label="View last report",
        width=PANEL_BTN_W,
        height=PANEL_BTN_H,
        callback=lambda: _on_view_last_report(app_state),
    )
    with dpg.tooltip(parent="view_last_report_btn"):
        dpg.add_text("Re-open the most recent session report in your browser.")


def _build_cursor_controls(app_state, settings) -> None:
    """Add cursor mode toggle, trail, and smoothing filter to the panel."""
    dpg.add_button(
        tag="cursor_toggle_btn",
        label=_cursor_label(settings),
        callback=lambda: _on_cursor_toggle(settings),
        width=PANEL_BTN_W,
        height=PANEL_BTN_H,
    )
    with dpg.tooltip(parent="cursor_toggle_btn"):
        dpg.add_text(
            "Switch between avatar and circle cursor.\n"
            "You can also click the cursor on screen."
        )
    app_state.update_cursor_toggle_label = lambda: update_cursor_toggle_label(settings)
    dpg.add_spacer(height=8)
    dpg.add_text("Cursor size")
    dpg.add_slider_int(
        tag="cursor_size_slider",
        default_value=settings.cursor_size,
        min_value=CURSOR_SIZE_MIN,
        max_value=CURSOR_SIZE_MAX,
        width=PANEL_SLIDER_W,
        format="%d px",
        callback=lambda s, v: _on_cursor_size_change(v, settings),
    )
    with dpg.tooltip(parent="cursor_size_slider"):
        dpg.add_text(
            "Adjust the circle cursor radius.\n"
            "You can also drag the cursor on screen to resize."
        )
    dpg.add_spacer(height=8)
    dpg.add_text("Sway trail")
    trail_rmap = {0: "None", 30: "Medium", 100: "Long"}
    current_label = trail_rmap.get(settings.trail_length, "Long")
    _btn_w = (PANEL_BTN_W - 8) // 3
    with dpg.group(horizontal=True):
        for lbl, val in [("None", 0), ("Medium", 30), ("Long", 100)]:
            tag = f"trail_btn_{lbl.lower()}"
            dpg.add_button(
                tag=tag,
                label=lbl,
                width=_btn_w,
                height=PANEL_BTN_H,
                callback=lambda s, a, u: _on_trail_change(u, settings),
                user_data=val,
            )
            with dpg.tooltip(parent=tag):
                dpg.add_text(
                    f"Trail length: {lbl}\n"
                    "Length of the historical position trail behind the cursor."
                )
    _update_trail_buttons(current_label)
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
    with dpg.tooltip(parent="filter_slider"):
        dpg.add_text("Frames averaged to reduce sensor noise.\n1 = no smoothing.")


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
    with dpg.tooltip(parent="zoom_slider"):
        dpg.add_text("Zoom the movement canvas.\nCtrl+Scroll also zooms.")
    dpg.add_spacer(height=4)
    dpg.add_button(
        label="Fit View to Bounding Box",
        tag="zoom_to_bbox_btn",
        callback=lambda: session_state.update({"action": "zoom_to_bbox_and_reset_pan"}),
        width=PANEL_BTN_W,
        height=PANEL_BTN_H,
    )
    with dpg.tooltip(parent="zoom_to_bbox_btn"):
        dpg.add_text("Zoom and pan to fit all recorded\nmovement within the view.")
    dpg.add_spacer(height=8)
    dpg.add_checkbox(
        tag="show_bbox_checkbox",
        label="Show bounding box",
        default_value=settings.show_bbox,
        callback=lambda s, v: _on_show_bbox_change(v, settings),
    )
    with dpg.tooltip(parent="show_bbox_checkbox"):
        dpg.add_text("Show or hide the movement bounding box on the canvas.")
    dpg.add_spacer(height=4)
    dpg.add_checkbox(
        tag="show_global_axes_checkbox",
        label="Show global axes",
        default_value=settings.show_global_axes,
        callback=lambda s, v: _on_show_global_axes_change(v, settings),
    )
    with dpg.tooltip(parent="show_global_axes_checkbox"):
        dpg.add_text("Solid crosshairs at screen centre\n(neutral stance reference).")
    dpg.add_spacer(height=4)
    dpg.add_checkbox(
        tag="show_local_axes_checkbox",
        label="Show local axes",
        default_value=settings.show_local_axes,
        callback=lambda s, v: _on_show_local_axes_change(v, settings),
    )
    with dpg.tooltip(parent="show_local_axes_checkbox"):
        dpg.add_text(
            "Dotted crosshairs at sway-bbox centre,\n"
            "bounded to the movement bounding box."
        )
    dpg.add_spacer(height=8)
    dpg.add_text("Targets")
    dpg.add_text("Dwell time (s)")
    dpg.add_input_float(
        tag="target_dwell_input",
        default_value=settings.target_dwell_seconds,
        min_value=TARGET_DWELL_MIN,
        max_value=TARGET_DWELL_MAX,
        step=TARGET_DWELL_STEP,
        format="%.1f",
        width=PANEL_BTN_W,
        callback=lambda s, v: _on_target_dwell_change(v, settings),
    )
    with dpg.tooltip(parent="target_dwell_input"):
        dpg.add_text(
            "Time the cursor must stay inside a target\n"
            "before the hit counter increases by one.\n"
            "Range 0–5 s in 0.1 s steps (0 = instant count)."
        )
    dpg.add_spacer(height=4)
    dpg.add_checkbox(
        tag="show_target_counter_checkbox",
        label="Show hit counter",
        default_value=settings.show_target_counter,
        callback=lambda s, v: _on_show_target_counter_change(v, settings),
    )
    with dpg.tooltip(parent="show_target_counter_checkbox"):
        dpg.add_text("Show or hide the on-screen target hit counter.")
    dpg.add_spacer(height=4)
    dpg.add_button(
        label="Reset hit counter",
        tag="reset_target_counter_btn",
        callback=lambda: session_state.update({"action": "reset_target_counter"}),
        width=PANEL_BTN_W,
        height=PANEL_BTN_H,
    )
    with dpg.tooltip(parent="reset_target_counter_btn"):
        dpg.add_text("Reset the target hit counter to zero.")
    dpg.add_spacer(height=8)
    dpg.add_text("Flip axis")
    _flip_icon_w = PANEL_BTN_H
    _flip_v_label = ICON_FLIP_VERTICAL if _theme_module.FA_ICON_FONT_SMALL else "V"
    _flip_h_label = ICON_FLIP_HORIZONTAL if _theme_module.FA_ICON_FONT_SMALL else "H"
    with dpg.group(horizontal=True):
        flip_v_btn = dpg.add_button(
            tag="flip_vertical_btn",
            label=_flip_v_label,
            width=_flip_icon_w,
            height=PANEL_BTN_H,
            callback=lambda: _on_flip_vertical_toggle(settings, app_state),
        )
        if _theme_module.FA_ICON_FONT_SMALL is not None:
            dpg.bind_item_font(flip_v_btn, _theme_module.FA_ICON_FONT_SMALL)
        dpg.add_text("Flip Vertical")
    with dpg.tooltip(parent="flip_vertical_btn"):
        dpg.add_text("Invert forward-back mapping on screen and in recordings.")
    dpg.add_spacer(height=4)
    with dpg.group(horizontal=True):
        flip_h_btn = dpg.add_button(
            tag="flip_horizontal_btn",
            label=_flip_h_label,
            width=_flip_icon_w,
            height=PANEL_BTN_H,
            callback=lambda: _on_flip_horizontal_toggle(settings, app_state),
        )
        if _theme_module.FA_ICON_FONT_SMALL is not None:
            dpg.bind_item_font(flip_h_btn, _theme_module.FA_ICON_FONT_SMALL)
        dpg.add_text("Flip Horizontal")
    with dpg.tooltip(parent="flip_horizontal_btn"):
        dpg.add_text("Invert left-right mapping on screen and in recordings.")
    _update_flip_buttons(settings)


def build_panel_controls(app_state, settings, session_state: dict) -> None:
    """Populate the settings panel with all control sections."""
    _build_section_header("RECORDING", accent_color=_theme_module.C_ACCENT_RECORDING)
    _build_recording_controls(app_state, settings)

    _build_section_header(
        "CURSOR & MOVEMENT", accent_color=_theme_module.C_ACCENT_CURSOR
    )
    _build_cursor_controls(app_state, settings)

    _build_section_header("VISUALISATION", accent_color=_theme_module.C_ACCENT_VISUAL)
    _build_visualisation_controls(app_state, settings, session_state)

    _build_section_header("CALIBRATION", accent_color=_theme_module.C_ACCENT_SESSION)
    _build_calibration_controls(app_state, settings, session_state)


def _on_trail_change(value: int, settings) -> None:
    """Update the trail length setting used for the historical cursor path."""
    apply_trail_length(settings, value)
    trail_rmap = {0: "None", 30: "Medium", 100: "Long"}
    _update_trail_buttons(trail_rmap.get(value, "Long"))


def _on_filter_change(value: int, settings, app_state) -> None:
    """Update the moving average filter window and trim the current filter buffer."""
    apply_filter_window(settings, app_state, value)


def _on_show_bbox_change(value: bool, settings) -> None:
    """Toggle bounding box visibility."""
    apply_setting_bool(settings, "show_bbox", value)


def _on_show_global_axes_change(value: bool, settings) -> None:
    """Toggle global (screen-centred) axis crosshairs."""
    apply_setting_bool(settings, "show_global_axes", value)


def _on_show_local_axes_change(value: bool, settings) -> None:
    """Toggle local (bbox-centred) axis crosshairs."""
    apply_setting_bool(settings, "show_local_axes", value)


def _on_target_dwell_change(value: float, settings) -> None:
    """Update the dwell time required to increment the hit counter."""
    clamped = apply_target_dwell_seconds(settings, value)
    if dpg.does_item_exist("target_dwell_input"):
        dpg.set_value("target_dwell_input", clamped)


def _on_show_target_counter_change(value: bool, settings) -> None:
    """Toggle on-screen target hit counter visibility."""
    apply_setting_bool(settings, "show_target_counter", value)


def _on_flip_vertical_toggle(settings, app_state) -> None:
    """Toggle vertical axis flip and reset sway trail/bbox extents."""
    apply_flip_vertical(settings, app_state)
    _update_flip_buttons(settings)


def _on_flip_horizontal_toggle(settings, app_state) -> None:
    """Toggle horizontal axis flip and reset sway trail/bbox extents."""
    apply_flip_horizontal(settings, app_state)
    _update_flip_buttons(settings)


def _on_zoom_change(value: float, settings, app_state) -> None:
    """Apply a new zoom factor and immediately rescale runtime extents."""
    apply_zoom_slider(settings, app_state, value)


# ---------------------------------------------------------------------------
# Calibration screens — drawn to viewport_drawlist each frame
# ---------------------------------------------------------------------------


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

    tag = _wii_texture_tags[1 if step == "on" else 0]
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

    cfg = dpg.get_item_configuration(_connection_texture_tag)
    iw_orig, ih_orig = cfg["width"], cfg["height"]
    scaled_h = int(0.8 * sh)
    scaled_w = int(scaled_h * iw_orig / ih_orig)
    img_x = sw // 2 - scaled_w // 2
    img_y = sh // 2 - scaled_h // 2
    dpg.draw_image(
        _connection_texture_tag,
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


# ---------------------------------------------------------------------------
# Main balance screen
# ---------------------------------------------------------------------------


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
                continue
            elapsed[idx] = elapsed.get(idx, 0.0) + dt
            if elapsed[idx] >= dwell_seconds:
                app_state.target_hit_count += 1
                elapsed.pop(idx, None)
                disarmed.add(idx)
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
        scaled_cursor = max(1, int(settings.cursor_size * settings.zoom_factor))
        dpg.draw_circle(
            (ball_x, ball_y),
            scaled_cursor,
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

    # Target hit counter — large centred number at top of canvas
    if settings.show_target_counter and toolbar_enabled:
        counter_str = str(app_state.target_hit_count)
        counter_font_size = 90
        counter_w = _measure_crisp_text_width(counter_str, counter_font_size)
        _crisp_text(
            (sw / 2 - counter_w / 2, sh * 0.08),
            counter_str,
            color=(20, 20, 20, 255),
            size=counter_font_size,
            parent=dl,
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
