# ui.py
# All rendering via Dear PyGui drawlist API.
# The viewport_drawlist draws directly onto the viewport background — no
# window chrome around the canvas. UI controls sit in a separate overlay window.

import math
import os
import time

import dearpygui.dearpygui as dpg

import wiibble.ui.theme as _theme_module
from wiibble.ui.theme import (
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
    ICON_INFINITY,
    STATS_TEXT_COLOR,
    TRAIL_COLOR_BASE,
    bind_text_font,
    get_stats_bar_color,
)
from wiibble.utils.constants import (
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
    ZOOM_MAX,
    ZOOM_MIN,
    ZOOM_SCALE,
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
        header_height = 128  # buffer enough for header, separator, spacing and window padding
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


# ---------------------------------------------------------------------------
# Per-widget theme caches — created lazily on first use
# ---------------------------------------------------------------------------
_trail_active_theme = None
_recording_active_theme = None


def _get_trail_active_theme():
    """Return (creating on demand) the highlighted theme for the active trail button."""
    global _trail_active_theme
    if _trail_active_theme is None or not dpg.does_item_exist(_trail_active_theme):
        with dpg.theme() as t:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(
                    dpg.mvThemeCol_Button, _theme_module.C_BRAND, category=dpg.mvThemeCat_Core
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
    if _recording_active_theme is None or not dpg.does_item_exist(_recording_active_theme):
        with dpg.theme() as t:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(
                    dpg.mvThemeCol_Button, (180, 50, 50, 255), category=dpg.mvThemeCat_Core
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_ButtonHovered, (200, 70, 70, 255), category=dpg.mvThemeCat_Core
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_ButtonActive, (220, 90, 90, 255), category=dpg.mvThemeCat_Core
                )
        _recording_active_theme = t
    return _recording_active_theme


def _update_trail_buttons(active_label: str) -> None:
    """Highlight the active trail selection button; clear highlight on the others."""
    for lbl in ("None", "Medium", "Long"):
        tag = f"trail_btn_{lbl.lower()}"
        if dpg.does_item_exist(tag):
            if lbl == active_label:
                dpg.bind_item_theme(tag, _get_trail_active_theme())
            else:
                dpg.bind_item_theme(tag, 0)


def _build_section_header(label: str, accent_color=None) -> None:
    """Render a section label with an optional coloured accent bar and a separator line."""
    dpg.add_spacer(height=PANEL_SECTION_SPACING)
    with dpg.group(horizontal=True):
        if accent_color is not None:
            accent_item = dpg.add_button(label="", width=4, height=18)
            with dpg.theme() as _accent_theme:
                with dpg.theme_component(dpg.mvButton):
                    dpg.add_theme_color(
                        dpg.mvThemeCol_Button, accent_color, category=dpg.mvThemeCat_Core
                    )
                    dpg.add_theme_color(
                        dpg.mvThemeCol_ButtonHovered, accent_color, category=dpg.mvThemeCat_Core
                    )
                    dpg.add_theme_color(
                        dpg.mvThemeCol_ButtonActive, accent_color, category=dpg.mvThemeCat_Core
                    )
            dpg.bind_item_theme(accent_item, _accent_theme)
            dpg.add_spacer(width=4)
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


def _on_cursor_size_change(value: int, settings) -> None:
    """Persist a new cursor size selection and update settings."""
    settings.cursor_size = value
    settings.save()


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
        dpg.bind_item_theme("start_recording_btn", 0)
        app_state.recording_indicator = False
        app_state.stopwatch_elapsed = 0.0
        return  # Prevent double start
    app_state.is_countdown = True
    app_state.countdown_value = 4
    # Use a sentinel value for indefinite recording; app.py checks settings.record_indefinite
    app_state.record_duration = settings.record_duration
    app_state.record_buffer = []
    app_state.recording_indicator = False
    app_state.stopwatch_elapsed = 0.0
    # change label of start button to "Stop Recording"
    dpg.set_item_label("start_recording_btn", "Stop Recording")
    dpg.bind_item_theme("start_recording_btn", _get_recording_theme())


def _build_session_buttons(session_state: dict) -> None:
    """Add session-level panel button: Restart."""
    _restart_btn = dpg.add_button(
        tag="restart_session_btn",
        label="Restart Session",
        callback=lambda: session_state.update({"action": "restart"}),
        width=PANEL_BTN_W,
        height=PANEL_BTN_H,
    )
    with dpg.tooltip(parent="restart_session_btn"):
        dpg.add_text("Reconnect and re-tare the board.")


def _clamp_body_weight(value: float) -> float:
    """Clamp body weight to the allowed settings range."""
    return max(BODY_WEIGHT_MIN, min(BODY_WEIGHT_MAX, float(value)))


def _on_body_weight_change(value: float, settings, app_state) -> None:
    """Persist a manual body weight and sync it to runtime state."""
    if value <= 0:
        return
    value = _clamp_body_weight(value)
    settings.body_weight_kg = value
    app_state.weight = value
    settings.save()
    if dpg.does_item_exist("body_weight_input"):
        dpg.set_value("body_weight_input", value)


def _on_calibrate_board(session_state: dict) -> None:
    """Request on-board weight calibration from the main loop."""
    session_state.update({"action": "calibrate"})


def _build_calibration_controls(app_state, settings, session_state: dict) -> None:
    """Add body weight input and on-board calibration button to the panel."""
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
            "Reference body weight for cursor normalization and recordings.\n"
            "Default is 70 kg if not set."
        )
    with dpg.tooltip(parent="calibrate_board_btn"):
        dpg.add_text(
            "Run step-off / step-on calibration to measure weight on the board.\n"
            "Updates this field when complete."
        )


def _open_recording_dir_picker(settings) -> None:
    """Open the Dear PyGui file dialog in directory mode (light theme override)."""
    documents = os.path.join(os.path.expanduser("~"), "Documents")
    default_dir = os.path.join(documents, "WIIBBLE", "recordings")
    initial = settings.recording_dir or default_dir

    # Create a more detailed light theme for the dialog if not already present
    if not dpg.does_item_exist("recording_dir_dialog_theme"):
        with dpg.theme(tag="recording_dir_dialog_theme"):
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(
                    dpg.mvThemeCol_WindowBg, (245, 245, 245, 255), category=dpg.mvThemeCat_Core
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_ChildBg, (255, 255, 255, 255), category=dpg.mvThemeCat_Core
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_Text, (20, 20, 20, 255), category=dpg.mvThemeCat_Core
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_Button, (220, 220, 220, 255), category=dpg.mvThemeCat_Core
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_ButtonHovered, (200, 200, 200, 255), category=dpg.mvThemeCat_Core
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_ButtonActive, (180, 180, 180, 255), category=dpg.mvThemeCat_Core
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_FrameBg, (235, 235, 235, 255), category=dpg.mvThemeCat_Core
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_FrameBgHovered,
                    (220, 220, 220, 255),
                    category=dpg.mvThemeCat_Core,
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_FrameBgActive, (200, 200, 200, 255), category=dpg.mvThemeCat_Core
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_SliderGrab, (107, 143, 168, 255), category=dpg.mvThemeCat_Core
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_SliderGrabActive,
                    (180, 180, 180, 255),
                    category=dpg.mvThemeCat_Core,
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_Header, (220, 220, 220, 255), category=dpg.mvThemeCat_Core
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_HeaderHovered, (200, 200, 200, 255), category=dpg.mvThemeCat_Core
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_HeaderActive, (180, 180, 180, 255), category=dpg.mvThemeCat_Core
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_Border, (180, 180, 180, 255), category=dpg.mvThemeCat_Core
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_ScrollbarBg, (235, 235, 235, 240), category=dpg.mvThemeCat_Core
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_ScrollbarGrab, (190, 220, 235, 255), category=dpg.mvThemeCat_Core
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
                    dpg.mvThemeCol_TitleBg, (250, 250, 250, 255), category=dpg.mvThemeCat_Core
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_TitleBgActive, (245, 245, 245, 255), category=dpg.mvThemeCat_Core
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_TitleBgCollapsed,
                    (250, 250, 250, 255),
                    category=dpg.mvThemeCat_Core,
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_MenuBarBg, (245, 245, 245, 255), category=dpg.mvThemeCat_Core
                )
                dpg.add_theme_style(dpg.mvStyleVar_ScrollbarSize, 16, category=dpg.mvThemeCat_Core)
                # Use very light colors for file dialog column header row (filename/type/size/date)
                dpg.add_theme_color(
                    dpg.mvThemeCol_Header, (252, 252, 252, 255), category=dpg.mvThemeCat_Core
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_HeaderHovered, (240, 240, 240, 255), category=dpg.mvThemeCat_Core
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_HeaderActive, (230, 230, 230, 255), category=dpg.mvThemeCat_Core
                )

    if not dpg.does_item_exist("recording_dir_dialog"):

        def _on_dir_picker(sender, app_data):
            chosen = app_data.get("file_path_name")
            if chosen:
                settings.recording_dir = chosen
                settings.save()
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
_DURATION_PRESETS = [(10, "10s"), (20, "20s"), (30, "30s"), (60, "60s"), (0, ICON_INFINITY)]


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
    """Apply a duration preset selection, sync the manual input, and update button highlight."""
    _on_record_duration_change(val, settings, app_state)
    _update_duration_preset_buttons(val)
    if dpg.does_item_exist("record_duration_input"):
        dpg.set_value("record_duration_input", val)


def _on_manual_duration_change(val: int, settings, app_state) -> None:
    """Apply a manually typed duration; clears preset highlight unless it matches a preset."""
    _on_record_duration_change(val, settings, app_state)
    preset_vals = {p[0] for p in _DURATION_PRESETS}
    _update_duration_preset_buttons(val if val in preset_vals else -1)


def _build_recording_controls(app_state, settings) -> None:
    """Add recording duration presets, manual input, and start/stop button to the panel."""
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
                callback=lambda s, a, u: _on_duration_preset_change(u, settings, app_state),
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
            "Custom duration in seconds (0 = record indefinitely).\nOr use the preset buttons above."
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
        dpg.add_text("Begin recording after a 3-second countdown.\nClick again to stop.")
    dpg.add_spacer(height=8)
    # Save location
    dpg.add_text("Save location")
    documents = os.path.join(os.path.expanduser("~"), "Documents")
    _default_dir = os.path.join(documents, "WIIBBLE", "recordings")
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
            "Switch between avatar and circle cursor.\nYou can also click the cursor on screen."
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
            "Adjust the circle cursor radius.\nYou can also drag the cursor on screen to resize."
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
                    f"Trail length: {lbl}\nLength of the historical position trail shown behind the cursor."
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
        tag="target_jelly_checkbox",
        label="Target jelly effect",
        default_value=settings.target_jelly,
        callback=lambda s, v: _on_target_jelly_change(v, settings),
    )
    with dpg.tooltip(parent="target_jelly_checkbox"):
        dpg.add_text("Animate targets with a jelly wobble when hit.")
    dpg.add_spacer(height=8)
    _clear_btn = dpg.add_button(
        tag="clear_screen_btn",
        label="Clear Screen",
        callback=lambda: session_state.update({"action": "clear"}),
        width=PANEL_BTN_W,
        height=PANEL_BTN_H,
    )
    with dpg.tooltip(parent="clear_screen_btn"):
        dpg.add_text("Remove all targets and the sway trail\nfrom the canvas.")


def build_panel_controls(app_state, settings, session_state: dict) -> None:
    """Populate the settings panel with all control sections."""
    _build_section_header("CALIBRATION", accent_color=_theme_module.C_ACCENT_SESSION)
    _build_calibration_controls(app_state, settings, session_state)

    _build_section_header("SESSION", accent_color=_theme_module.C_ACCENT_SESSION)
    _build_session_buttons(session_state)

    _build_section_header("RECORDING", accent_color=_theme_module.C_ACCENT_RECORDING)
    _build_recording_controls(app_state, settings)

    _build_section_header("CURSOR & MOVEMENT", accent_color=_theme_module.C_ACCENT_CURSOR)
    _build_cursor_controls(app_state, settings)

    _build_section_header("VISUALISATION", accent_color=_theme_module.C_ACCENT_VISUAL)
    _build_visualisation_controls(app_state, settings, session_state)


def _on_trail_change(value: int, settings) -> None:
    """Update the trail length setting used for the historical cursor path."""
    settings.trail_length = value
    settings.save()
    trail_rmap = {0: "None", 30: "Medium", 100: "Long"}
    _update_trail_buttons(trail_rmap.get(value, "Long"))


def _on_filter_change(value: int, settings, app_state) -> None:
    """Update the moving average filter window and trim the current filter buffer."""
    settings.filter_window = value
    if len(app_state.filter_buffer) > value:
        app_state.filter_buffer = app_state.filter_buffer[-value:]
    settings.save()


def _on_show_bbox_change(value: bool, settings) -> None:
    """Toggle bounding box visibility."""
    settings.show_bbox = value
    settings.save()


def _on_target_jelly_change(value: bool, settings) -> None:
    """Toggle target jelly animation on hit."""
    settings.target_jelly = value
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

    tag = _wii_texture_tags[2 if step == "on" else 0]
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
    for idx, target in enumerate(app_state.clicked_locations):
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
        # Spawn jelly oscillation on False→True transition
        prev = app_state._prev_hit_states.get(idx, False)
        if hit and not prev and settings.target_jelly:
            app_state._jelly_ages[idx] = 0
        app_state._prev_hit_states[idx] = hit
        # Compute display radius with damped sinusoidal jelly if active
        age = app_state._jelly_ages.get(idx, -1)
        if age >= 0 and settings.target_jelly:
            jelly_r = scaled_radius * (1.0 + 0.25 * math.exp(-0.13 * age) * math.sin(0.55 * age))
            age += 1
            if age >= 50:
                del app_state._jelly_ages[idx]
            else:
                app_state._jelly_ages[idx] = age
        else:
            jelly_r = scaled_radius
        fill = (0, 255, 0, 200) if hit else (255, 0, 0, 200)
        dpg.draw_circle((vx, vy), max(1.0, jelly_r), color=fill, fill=fill, parent=dl)

    # (ripple ring loop removed — replaced by per-target jelly oscillation above)

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
        scaled_cursor = max(1, int(settings.cursor_size * settings.zoom_factor))
        dpg.draw_circle(
            (ball_x, ball_y), scaled_cursor, color=CURSOR_COLOR, fill=CURSOR_COLOR, parent=dl
        )

    # Bounding box — max_x/min_x are relative coordinate extents (not viewport coords).
    # They need to be offset by canvas centre (cx, cy) to get viewport coords.
    if settings.show_bbox:
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
