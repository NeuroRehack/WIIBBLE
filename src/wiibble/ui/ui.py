# ui.py
# All rendering via Dear PyGui drawlist API.
# The viewport_drawlist draws directly onto the viewport background — no
# window chrome around the canvas. UI controls sit in a separate overlay window.

import logging

import dearpygui.dearpygui as dpg

import wiibble.ui.theme as _theme_module
from wiibble.ui.theme import (
    BAR_GREY_COLOR,
    ICON_INFINITY,
    STATS_TEXT_COLOR,
    bind_text_font,
    get_stats_bar_color,
)
from wiibble.utils.constants import (
    PANEL_SECTION_SPACING,
    PANEL_TOGGLE_BTN_SIZE,
    PANEL_W,
    QUICK_ACCESS_GAP,
    QUICK_ACCESS_MARGIN,
    QUICK_ACCESS_WINDOW_PAD,
    RECORDING_INDICATOR_DOT_RADIUS,
)

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Layout constants — all proportional to viewport dimensions.
# Change a value here and it propagates everywhere.
# ---------------------------------------------------------------------------
STATS_STRIP_H = 50  # height of bottom stats strip in pixels
STS_TRANSITION_ZONE_COLOR = (55, 58, 65, 255)
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


# ---------------------------------------------------------------------------
# Texture registry — images must be loaded into DPG's texture system
# ---------------------------------------------------------------------------

_textures_loaded = False
_wii_texture_tags = []
_person_texture_tag = "person_image"
_connection_texture_tag = "connection_image"


# Cached stats values — stats drawlist only redraws when these change.
# This eliminates the sub-pixel jitter that caused blurry text.
_stats_cache = {
    "left": -1,
    "weight": -1,
    "right": -1,
    "sts_sit_pct": -1,
    "sts_stand_pct": -1,
    "sts_gauge": False,
}


def _clear_stats_cache() -> None:
    """Reset the stats-bar draw cache so the next update redraws."""
    for key in _stats_cache:
        if isinstance(_stats_cache[key], bool):
            _stats_cache[key] = False
        else:
            _stats_cache[key] = -1


def build_stats_bar(app_state) -> None:
    """Create or reset the overlay stats drawlist for the main screen."""
    if not dpg.does_item_exist("stats_dl"):
        dpg.add_viewport_drawlist(tag="stats_dl", front=False)
    dpg.delete_item("stats_dl", children_only=True)
    _clear_stats_cache()


def set_stats_bar_visible(visible: bool) -> None:
    """Show or hide the bottom stats overlay (e.g. during calibration screens)."""
    if not dpg.does_item_exist("stats_dl"):
        return
    dpg.configure_item("stats_dl", show=visible)
    if not visible:
        dpg.delete_item("stats_dl", children_only=True)
        _clear_stats_cache()


def update_stats_bar(
    perc_left: float,
    perc_right: float,
    curr_weight: float,
    calib_weight: float,
    settings=None,
) -> None:
    """Draw the live left/right distribution and weight stats overlay."""
    left_val = int(perc_left * 100)
    weight_val = int(curr_weight)
    right_val = int(perc_right * 100)
    sts_gauge = bool(settings and settings.sts_enabled)
    sts_sit_pct = int(settings.sts_sit_threshold_pct) if sts_gauge else -1
    sts_stand_pct = int(settings.sts_stand_threshold_pct) if sts_gauge else -1

    if (
        left_val == _stats_cache["left"]
        and weight_val == _stats_cache["weight"]
        and right_val == _stats_cache["right"]
        and sts_gauge == _stats_cache["sts_gauge"]
        and sts_sit_pct == _stats_cache["sts_sit_pct"]
        and sts_stand_pct == _stats_cache["sts_stand_pct"]
    ):
        return

    _stats_cache["left"] = left_val
    _stats_cache["weight"] = weight_val
    _stats_cache["right"] = right_val
    _stats_cache["sts_gauge"] = sts_gauge
    _stats_cache["sts_sit_pct"] = sts_sit_pct
    _stats_cache["sts_stand_pct"] = sts_stand_pct

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
        (x0, bar_top),
        (x1, bar_bot),
        fill=bar_color,
        color=bar_color,
        parent="stats_dl",
    )

    if sts_gauge:
        _draw_sts_threshold_markers(bar_top, bar_bot, sw, settings, "stats_dl")

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
    """Create the top-left quick-access bar (gear, clear, fit view, reset counter)."""
    if dpg.does_item_exist("left_quick_access_window"):
        dpg.delete_item("left_quick_access_window")

    clear_label = (
        _theme_module.ICON_ERASER if _theme_module.FA_ICON_FONT is not None else "Clr"
    )
    fit_view_label = (
        _theme_module.ICON_FIT_VIEW if _theme_module.FA_ICON_FONT is not None else "Fit"
    )
    reset_label = (
        _theme_module.ICON_COUNTER_RESET
        if _theme_module.FA_ICON_FONT is not None
        else "Rst"
    )
    btn = PANEL_TOGGLE_BTN_SIZE
    margin = QUICK_ACCESS_MARGIN
    window_w, window_h = _left_quick_access_window_size(4)

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
            callback=lambda: session_state.update(
                {"action": "clear", "action_detail": "quick access"}
            ),
            width=btn,
            height=btn,
        )
        fit_view_btn = dpg.add_button(
            tag="fit_view_quick_btn",
            label=fit_view_label,
            callback=lambda: session_state.update(
                {
                    "action": "zoom_to_bbox_and_reset_pan",
                    "action_detail": "quick access",
                }
            ),
            width=btn,
            height=btn,
        )
        reset_btn = dpg.add_button(
            tag="reset_counter_quick_btn",
            label=reset_label,
            callback=lambda: session_state.update(
                {"action": "reset_target_counter", "action_detail": "quick access"}
            ),
            width=btn,
            height=btn,
        )
        if _theme_module.FA_ICON_FONT is not None:
            dpg.bind_item_font(fit_view_btn, _theme_module.FA_ICON_FONT)
            dpg.bind_item_font(reset_btn, _theme_module.FA_ICON_FONT)

    with dpg.tooltip(parent="fit_view_quick_btn"):
        dpg.add_text(
            "Fit View: zoom and pan to fit all recorded\nmovement within the view."
        )
    with dpg.tooltip(parent="reset_counter_quick_btn"):
        dpg.add_text("Reset target hit and sit-to-stand rep counters to zero.")

    if _theme_module.FA_ICON_FONT is not None:
        dpg.bind_item_font("panel_float_btn", _theme_module.FA_ICON_FONT)
        dpg.bind_item_font("clear_screen_quick_btn", _theme_module.FA_ICON_FONT)

    with dpg.tooltip(parent="clear_screen_quick_btn"):
        dpg.add_text(
            "Clear Screen: remove targets and sway trail.\nShortcut: Ctrl+Shift+C"
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
            callback=lambda: _on_start_recording(
                app_state, settings, source="quick access"
            ),
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
        dpg.configure_item("fit_view_quick_btn", show=True)
        dpg.configure_item("reset_counter_quick_btn", show=True)
        dpg.set_item_pos("left_quick_access_window", (PANEL_W + 8, margin))
        window_w, window_h = _left_quick_access_window_size(3)
    else:
        dpg.configure_item("panel_float_btn", show=True)
        dpg.configure_item("clear_screen_quick_btn", show=True)
        dpg.configure_item("fit_view_quick_btn", show=True)
        dpg.configure_item("reset_counter_quick_btn", show=True)
        dpg.set_item_pos("left_quick_access_window", (margin, margin))
        window_w, window_h = _left_quick_access_window_size(4)

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
        "fit_view_quick_btn",
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


def collapse_settings_panel(session_state: dict, *, source: str = "control") -> bool:
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
    log.info("Settings panel closed (%s)", source)
    return True


def show_settings_panel(session_state: dict, *, source: str = "control") -> None:
    """Show the settings panel."""
    session_state["toolbar_visible"] = True
    if dpg.does_item_exist("control_panel"):
        dpg.configure_item("control_panel", show=True)
    update_left_quick_access_layout(
        True,
        session_state.get("toolbar_enabled", False),
    )
    session_state["action"] = "toolbar_toggled"
    log.info("Settings panel opened (%s)", source)


# ---------------------------------------------------------------------------
# Per-widget theme caches — created lazily on first use
# ---------------------------------------------------------------------------
_trail_active_theme = None
_recording_active_theme = None
_recording_quick_idle_theme = None
_recording_quick_active_theme = None


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


# Duration preset values (seconds); 0 = indefinite
_DURATION_PRESETS = [
    (10, "10s"),
    (20, "20s"),
    (30, "30s"),
    (60, "60s"),
    (0, ICON_INFINITY),
]


# ---------------------------------------------------------------------------
# Calibration screens — drawn to viewport_drawlist each frame
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Main balance screen
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Re-exports from split UI modules (backward-compatible public API)
# ---------------------------------------------------------------------------
from wiibble.ui.canvas_draw import (  # noqa: E402, F401
    _draw_sts_threshold_markers,
    _format_record_limit,
    _recording_indicator_layout,
    _target_hit_at_point,
    dashed_line_segments,
    draw_connection_failed_screen,
    draw_connection_screen,
    draw_main_screen,
    draw_reference_weight_instruction,
    draw_step_instruction,
    update_target_dwell,
)
from wiibble.ui.cursor_geometry import screen_cursor_radius  # noqa: E402, F401
from wiibble.ui.draw_helpers import (  # noqa: E402, F401
    crisp_icon_text as _crisp_icon_text,
    crisp_text as _crisp_text,
    estimate_text_width as _estimate_text_width,
    measure_crisp_text_width as _measure_crisp_text_width,
)
from wiibble.ui.settings_panel import (  # noqa: E402, F401
    _format_tare_status,
    _on_start_recording,
    _on_zoom_change,
    _relative_tare_label,
    build_panel_controls,
    format_sts_live_status,
    sync_report_progress_ui,
    update_cursor_toggle_label,
    update_sts_live_status_label,
    update_tare_status_label,
)
from wiibble.ui.textures import (  # noqa: E402, F401
    ensure_textures_loaded,
    get_person_image_size,
    get_wii_image_size,
)
