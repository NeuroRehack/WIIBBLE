"""WIIBBLE application runtime.

This module contains the main session lifecycle, device connection flow,
DearPyGui UI glue code, and the primary render + recording loop.
"""

# app.py
import logging
import math
import time

import dearpygui.dearpygui as dpg
import hid

import theme as _theme_module
from board_connection import try_connection
from calibration import sensitivity_calibration, wait_for_tare
from constants import (
    COORD_SCALE,
    CURSOR_HIT_FRACTION,
    CURSOR_HIT_RADIUS_CIRCLE,
    DLL_RELATIVE_PATH,
    FILTER_MAX,
    FILTER_MIN,
    GEAR_BTN_SIZE,
    PRODUCT_ID,
    SENSITIVITY_MAX,
    SENSITIVITY_MIN,
    TOOLBAR_BTN_H,
    TOOLBAR_BTN_W_MD,
    TOOLBAR_BTN_W_SM,
    TOOLBAR_COMBO_W,
    TOOLBAR_FULL_H,
    TOOLBAR_SLIDER_W,
    TOOLBAR_SPACER_MD,
    TOOLBAR_SPACER_SM,
    VENDOR_ID,
    ZOOM_MAX,
    ZOOM_MIN,
    ZOOM_SCALE,
    ZOOM_SPEED,
)
from data_processing import (
    apply_filter,
    calculate_coordinates,
    calculate_force_deviation_kg,
    parse_data,
    read_data,
    tare,
)
from mock_board import MockHIDDevice
from recording import _save_recording_csv
from resources import resource_path
from theme import BAR_GREY_COLOR, ICON_COG, STATS_TEXT_COLOR, bind_text_font, get_stats_bar_color
from ui import (
    STATS_FONT_MIN,
    STATS_FONT_SCALE,
    STATS_STRIP_H,
    draw_connection_failed_screen,
    draw_connection_screen,
    draw_main_screen,
    ensure_textures_loaded,
)

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Board connection
# ---------------------------------------------------------------------------


def connect_wii_board(use_mock: bool = False, mock_scenario: str = "sway"):
    """Return an open HID device (real or mock)."""
    if use_mock:
        device = MockHIDDevice.from_scenario(mock_scenario)
        device.open(VENDOR_ID, PRODUCT_ID)
        log.info("Using MockHIDDevice (scenario: %s)", mock_scenario)
        return device
    try:
        log.info("Connecting to Wii Balance Board...")
        device = hid.device()
        device.open(VENDOR_ID, PRODUCT_ID)
        log.info("Connected successfully!")
        return device
    except IOError as e:
        log.error("Failed to connect: %s", e)
        return None


def _try_connection_loop(dl, app_state, use_mock: bool = False) -> bool:
    """
    Show connection screen and loop until board connects.
    Returns True on success, False if window closed.
    Skipped entirely in mock mode.
    """
    if use_mock:
        log.debug("Skipping connection screen (mock mode).")
        return True

    while dpg.is_dearpygui_running():
        # Show "Trying to connect" while attempting
        dpg.delete_item(dl, children_only=True)
        draw_connection_screen(dl, app_state)
        dpg.render_dearpygui_frame()

        result = try_connection(resource_path(DLL_RELATIVE_PATH))
        if result == 0:
            return True

        # Show failed screen and wait for Enter key
        while dpg.is_dearpygui_running():
            dpg.delete_item(dl, children_only=True)
            draw_connection_failed_screen(dl, app_state)
            dpg.render_dearpygui_frame()
            if dpg.is_key_pressed(dpg.mvKey_Return):
                # Show retrying feedback immediately before next attempt
                dpg.delete_item(dl, children_only=True)
                draw_connection_screen(dl, app_state)
                dpg.render_dearpygui_frame()
                break

    return False


# ---------------------------------------------------------------------------
# UI control panel
# ---------------------------------------------------------------------------


def _get_gear_label() -> str:
    """Return the label used for the collapsed toolbar button."""
    # Access FA_ICON_FONT via module to get the live value, not the import-time None
    return ICON_COG if _theme_module.FA_ICON_FONT is not None else "[=]"


def _toggle_toolbar(session_state: dict) -> None:
    """Toggle the toolbar visibility state for the session."""
    visible = not session_state.get("toolbar_visible", False)
    session_state["toolbar_visible"] = visible
    if visible:
        # Show full toolbar, hide floating gear
        if dpg.does_item_exist("control_panel"):
            dpg.configure_item("control_panel", show=True)
        if dpg.does_item_exist("gear_btn_window"):
            dpg.configure_item("gear_btn_window", show=False)
    else:
        # Hide full toolbar, show floating gear
        if dpg.does_item_exist("control_panel"):
            dpg.configure_item("control_panel", show=False)
        if dpg.does_item_exist("gear_btn_window"):
            dpg.configure_item("gear_btn_window", show=True)
    session_state["action"] = "toolbar_toggled"


# --- Cursor toggle helpers (top-level) ---
def _cursor_label(settings):
    """Return the current cursor mode label for display in the toolbar."""
    return f"Cursor: {'Avatar' if settings.cursor_mode == 'avatar' else 'Circle'}"


def update_cursor_toggle_label(settings):
    """Update the toolbar cursor button label to reflect the current mode."""
    dpg.set_item_label("cursor_toggle_btn", _cursor_label(settings))


def _on_cursor_toggle(settings):
    """Toggle the cursor display mode and update the toolbar label."""
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


def _build_toolbar_controls(app_state, settings, session_state: dict) -> None:
    """Add the toolbar control widgets into the current DearPyGui context."""
    dpg.add_button(
        label="RESTART",
        callback=lambda: session_state.update({"action": "restart"}),
        width=TOOLBAR_BTN_W_SM,
        height=TOOLBAR_BTN_H,
    )
    dpg.add_button(
        label="RESET SCREEN",
        callback=lambda: session_state.update({"action": "reset"}),
        width=TOOLBAR_BTN_W_MD,
        height=TOOLBAR_BTN_H,
    )
    dpg.add_spacer(width=TOOLBAR_SPACER_MD)
    # --- S5: Recording duration input and Start Recording button ---
    dpg.add_text("Record Duration (s):")
    dpg.add_input_int(
        tag="record_duration_input",
        default_value=int(settings.record_duration),
        min_value=1,
        max_value=120,
        width=80,
        callback=lambda s, v: _on_record_duration_change(v, settings, app_state),
    )
    dpg.add_spacer(width=TOOLBAR_SPACER_SM)
    dpg.add_button(
        tag="start_recording_btn",
        label="Start Recording",
        width=TOOLBAR_BTN_W_SM,
        height=TOOLBAR_BTN_H,
        callback=lambda: _on_start_recording(app_state, settings),
        enabled=not app_state.is_recording and not app_state.is_countdown,
    )

    # --- Cursor toggle button ---
    dpg.add_button(
        tag="cursor_toggle_btn",
        label=_cursor_label(settings),
        callback=lambda: _on_cursor_toggle(settings),
        width=TOOLBAR_BTN_W_SM,
        height=TOOLBAR_BTN_H,
    )
    # Expose label update function for use elsewhere
    app_state.update_cursor_toggle_label = lambda: update_cursor_toggle_label(settings)
    dpg.add_spacer(width=TOOLBAR_SPACER_MD)
    dpg.add_text("Trail:")
    trail_items = ["None", "Medium", "Long"]
    trail_map = {"None": 0, "Medium": 30, "Long": 100}
    trail_rmap = {0: "None", 30: "Medium", 100: "Long"}
    current_label = trail_rmap.get(settings.trail_length, "Long")
    dpg.add_combo(
        tag="trail_combo",
        items=trail_items,
        default_value=current_label,
        width=TOOLBAR_COMBO_W,
        callback=lambda s, v: _on_trail_change(trail_map[v], settings),
    )
    dpg.add_spacer(width=TOOLBAR_SPACER_MD)
    dpg.add_text("Filter:")
    dpg.add_slider_int(
        tag="filter_slider",
        default_value=settings.filter_window,
        min_value=FILTER_MIN,
        max_value=FILTER_MAX,
        width=TOOLBAR_SLIDER_W,
        format="%d frames",
        callback=lambda s, v: _on_filter_change(v, settings, app_state),
    )
    dpg.add_spacer(width=TOOLBAR_SPACER_MD)
    dpg.add_text("Zoom:")
    dpg.add_slider_float(
        tag="zoom_slider",
        default_value=settings.zoom_factor,
        min_value=ZOOM_MIN,
        max_value=ZOOM_MAX,
        width=TOOLBAR_SLIDER_W,
        format="%.2fx",
        callback=lambda s, v: _on_zoom_change(v, settings, app_state),
    )
    dpg.add_spacer(width=TOOLBAR_SPACER_SM)
    dpg.add_button(
        label="Auto-Scale",
        tag="zoom_to_bbox_btn",
        callback=lambda: session_state.update({"action": "zoom_to_bbox"}),
        width=TOOLBAR_BTN_W_SM,
        height=TOOLBAR_BTN_H,
    )
    dpg.add_spacer(width=TOOLBAR_SPACER_MD)
    # --- S6: Sensitivity slider ---
    dpg.add_text("Sensitivity:")
    dpg.add_slider_float(
        tag="sensitivity_slider",
        default_value=settings.sensitivity,
        min_value=SENSITIVITY_MIN,
        max_value=SENSITIVITY_MAX,
        width=TOOLBAR_SLIDER_W,
        format="%.2fx",
        callback=lambda s, v: _on_sensitivity_change(v, settings),
    )
    dpg.add_spacer(width=TOOLBAR_SPACER_MD)
    # --- Pan: Reset Pan button ---
    dpg.add_button(
        label="Reset Pan",
        tag="reset_pan_btn",
        callback=lambda: session_state.update({"action": "reset_pan"}),
        width=TOOLBAR_BTN_W_SM,
        height=TOOLBAR_BTN_H,
    )


def _build_control_panel(app_state, settings, session_state: dict) -> None:
    """
    Builds two windows that are mutually exclusive:

    control_panel     — full opaque toolbar (expanded state)
    gear_btn_window   — tiny no_background floating button (collapsed state)

    Canvas always fills full viewport. Toolbar windows float on top.
    """
    sw = app_state.screen_width

    # --- Full toolbar ---
    with dpg.window(
        tag="control_panel",
        no_title_bar=True,
        no_resize=True,
        no_move=True,
        no_scrollbar=False,  # allow horizontal scroll on small screens
        no_collapse=True,
        no_scroll_with_mouse=True,  # don't hijack mouse wheel on canvas
        horizontal_scrollbar=True,
        pos=(0, 0),
        width=sw,
        height=TOOLBAR_FULL_H,
        show=False,
    ):
        with dpg.group(horizontal=True):
            dpg.add_button(
                tag="toggle_btn",
                label=_get_gear_label(),
                callback=lambda: _toggle_toolbar(session_state),
                width=GEAR_BTN_SIZE,
                height=GEAR_BTN_SIZE,
            )
            dpg.add_spacer(width=8)
            with dpg.group(tag="settings_group", horizontal=True):
                _build_toolbar_controls(app_state, settings, session_state)
    # no_background=True means zero DPG chrome — just the button pixel-perfect
    if dpg.does_item_exist("gear_btn_window"):
        dpg.delete_item("gear_btn_window")
    with dpg.window(
        tag="gear_btn_window",
        no_title_bar=True,
        no_resize=True,
        no_move=True,
        no_scrollbar=True,
        no_collapse=True,
        no_background=True,
        pos=(4, 4),
        width=GEAR_BTN_SIZE + 4,
        height=GEAR_BTN_SIZE + 4,
        show=session_state.get("toolbar_enabled", False),
    ):
        dpg.add_button(
            tag="gear_float_btn",
            label=_get_gear_label(),
            callback=lambda: _toggle_toolbar(session_state),
            width=GEAR_BTN_SIZE,
            height=GEAR_BTN_SIZE,
        )

    # Bind icon font to gear buttons if FontAwesome loaded successfully
    if _theme_module.FA_ICON_FONT is not None:
        dpg.bind_item_font("toggle_btn", _theme_module.FA_ICON_FONT)
        dpg.bind_item_font("gear_float_btn", _theme_module.FA_ICON_FONT)


def _on_trail_change(value: int, settings) -> None:
    """Update the trail length setting used for the historical cursor path."""
    settings.trail_length = value
    settings.save()


def _on_filter_change(value: int, settings, app_state) -> None:
    """Update the moving average filter window and trim the current filter buffer."""
    settings.filter_window = value
    # Trim buffer immediately if window shrank
    if len(app_state.filter_buffer) > value:
        app_state.filter_buffer = app_state.filter_buffer[-value:]
    settings.save()


def _on_zoom_change(value: float, settings, app_state) -> None:
    """Apply a new zoom factor and immediately rescale runtime extents."""
    value = ZOOM_SCALE**value
    settings.zoom_factor = value
    # Immediately rescale zoomed extents so bounding box updates on slider drag
    app_state.zoomed_max_x = app_state.raw_max_x * value
    app_state.zoomed_max_y = app_state.raw_max_y * value
    app_state.zoomed_min_x = app_state.raw_min_x * value
    app_state.zoomed_min_y = app_state.raw_min_y * value
    settings.save()


def _on_sensitivity_change(value: float, settings) -> None:
    """Adjust cursor movement sensitivity by scaling the effective weight divisor."""
    settings.sensitivity = value
    settings.save()


def _update_recording_frame(
    now: float,
    record_start_time,
    app_state,
    settings,
    top_left: float,
    top_right: float,
    bottom_left: float,
    bottom_right: float,
):
    """Advance recording state and append a CSV row for the current frame."""
    if app_state.is_recording:
        elapsed = now - (record_start_time if record_start_time else app_state.record_start)
        app_state.stopwatch_elapsed = elapsed
        x_kg, y_kg = calculate_force_deviation_kg(top_left, top_right, bottom_left, bottom_right)
        app_state.record_buffer.append((elapsed, x_kg, y_kg))
        if elapsed >= app_state.record_duration:
            app_state.is_recording = False
            app_state.recording_indicator = False
            app_state.stopwatch_elapsed = 0.0
            dpg.set_item_label("start_recording_btn", "Start Recording")
            _save_recording_csv(app_state.record_buffer)
            app_state.record_buffer = []
    return record_start_time


def _flush_record_buffer_if_complete(app_state) -> None:
    """Save the remaining recording buffer if recording has stopped."""
    if not app_state.is_recording and app_state.record_buffer:
        _save_recording_csv(app_state.record_buffer)
        app_state.record_buffer = []
        app_state.recording_indicator = False
        app_state.stopwatch_elapsed = 0.0


def _update_countdown_and_recording(
    now,
    last_countdown_tick,
    record_start_time,
    app_state,
    settings,
    top_left,
    top_right,
    bottom_left,
    bottom_right,
):
    """Advance countdown and recording state for the current frame."""
    if app_state.is_countdown:
        if now - last_countdown_tick >= 1.0:
            app_state.countdown_value -= 1
            last_countdown_tick = now
            if app_state.countdown_value <= 0:
                app_state.is_countdown = False
                app_state.is_recording = True
                app_state.recording_indicator = True
                record_start_time = now
                app_state.record_start = now
                app_state.record_buffer = []
                app_state.stopwatch_elapsed = 0.0

    record_start_time = _update_recording_frame(
        now,
        record_start_time,
        app_state,
        settings,
        top_left,
        top_right,
        bottom_left,
        bottom_right,
    )
    return record_start_time, last_countdown_tick


def _handle_viewport_resize(app_state, session_state):
    """Update app dimensions and toolbar visibility on viewport resize."""
    vw = dpg.get_viewport_width()
    vh = dpg.get_viewport_height()
    if vw == app_state.screen_width and vh == app_state.screen_height:
        return

    app_state.screen_width = vw
    app_state.screen_height = vh
    toolbar_currently_visible = session_state.get("toolbar_visible", False)
    toolbar_enabled = session_state.get("toolbar_enabled", False)
    dpg.configure_item("control_panel", width=vw, show=toolbar_currently_visible)
    if dpg.does_item_exist("gear_btn_window"):
        dpg.configure_item(
            "gear_btn_window",
            show=toolbar_enabled and not toolbar_currently_visible,
        )
    # stats_dl redraws itself at correct position on next value change


def _handle_session_action(action, device, dl, app_state, settings, session_state):
    """Process a toolbar action request and return a loop result if a session restart is needed."""
    if action == "restart":
        device.close()
        dpg.delete_item(dl)
        return 0
    if action == "reset":
        app_state.clicked_locations = []
        app_state.historical_coords = [(0, 0)] * settings.trail_length
        app_state.zoomed_max_x = app_state.zoomed_max_y = 0.0
        app_state.zoomed_min_x = app_state.zoomed_min_y = 0.0
        app_state.raw_max_x = app_state.raw_max_y = 0.0
        app_state.raw_min_x = app_state.raw_min_y = 0.0
        app_state.pan_offset_x = 0.0
        app_state.pan_offset_y = 0.0
        session_state["action"] = None
        return None
    if action == "zoom_to_bbox":
        _on_zoom_to_bbox(
            app_state.raw_max_x,
            app_state.raw_max_y,
            app_state.raw_min_x,
            app_state.raw_min_y,
            app_state,
            settings,
        )
        app_state.zoomed_max_x = app_state.raw_max_x * settings.zoom_factor
        app_state.zoomed_max_y = app_state.raw_max_y * settings.zoom_factor
        app_state.zoomed_min_x = app_state.raw_min_x * settings.zoom_factor
        app_state.zoomed_min_y = app_state.raw_min_y * settings.zoom_factor
        session_state["action"] = None
        return None
    if action == "reset_pan":
        app_state.pan_offset_x = 0.0
        app_state.pan_offset_y = 0.0
        session_state["action"] = None
        return None
    if action == "pan_changed":
        session_state["action"] = None
        return None
    if action == "toolbar_toggled":
        session_state["action"] = None
        return None
    return None


def _prepare_session(dl, app_state, settings, session_state, args):
    """Run connection, tare, and calibration startup steps before the main loop."""
    try:
        connected = _try_connection_loop(dl, app_state, use_mock=args.mock)
        if not connected:
            return None
    except Exception:
        log.exception("Connection failed")
        return None

    device = connect_wii_board(use_mock=args.mock, mock_scenario=args.mock_scenario)
    if not device:
        return None

    try:
        device.set_nonblocking(1)
    except Exception:
        pass

    dpg.delete_item(dl, children_only=True)
    draw_connection_screen(dl, app_state)
    dpg.render_dearpygui_frame()

    wait_for_tare(device, dl, app_state)
    try:
        tare(device, app_state.data_struct)
    except Exception:
        log.exception("Failed to tare")
        device.close()
        return None

    on_start = device.trigger_step_on if hasattr(device, "trigger_step_on") else None
    calibrated_weight = sensitivity_calibration(device, dl, app_state, on_start=on_start)
    if calibrated_weight == -1:
        device.close()
        return None

    app_state.weight = calibrated_weight
    session_state["toolbar_enabled"] = True
    if dpg.does_item_exist("gear_btn_window"):
        dpg.configure_item("gear_btn_window", show=True)

    return device


def _render_main_screen_frame(
    device,
    dl,
    app_state,
    settings,
    session_state,
    top_left: float,
    top_right: float,
    bottom_left: float,
    bottom_right: float,
):
    """Read sensor data and render the main session canvas when data is available."""
    data = read_data(device)
    if not data:
        return top_left, top_right, bottom_left, bottom_right

    corners = parse_data(data, app_state.data_struct)
    smoothed = apply_filter(corners, app_state.filter_buffer, settings.filter_window)
    top_right = smoothed["top_right"]
    bottom_right = smoothed["bottom_right"]
    top_left = smoothed["top_left"]
    bottom_left = smoothed["bottom_left"]

    effective_weight = app_state.weight / max(settings.sensitivity, 0.01)
    raw_x, raw_y = calculate_coordinates(
        top_left,
        top_right,
        bottom_left,
        bottom_right,
        weight=effective_weight,
        screen_width=app_state.screen_width,
        screen_height=app_state.screen_height,
        zoom=1.0,
    )

    app_state.raw_max_x = max(app_state.raw_max_x, raw_x)
    app_state.raw_max_y = max(app_state.raw_max_y, raw_y)
    app_state.raw_min_x = min(app_state.raw_min_x, raw_x)
    app_state.raw_min_y = min(app_state.raw_min_y, raw_y)

    x = raw_x * settings.zoom_factor
    y = raw_y * settings.zoom_factor
    app_state.zoomed_max_x = max(app_state.zoomed_max_x, x)
    app_state.zoomed_max_y = max(app_state.zoomed_max_y, y)
    app_state.zoomed_min_x = min(app_state.zoomed_min_x, x)
    app_state.zoomed_min_y = min(app_state.zoomed_min_y, y)

    ball_x = int(app_state.screen_width // 2 + x + app_state.pan_offset_x)
    ball_y = int(app_state.screen_height // 2 + y + app_state.pan_offset_y)
    app_state.ball_x = ball_x
    app_state.ball_y = ball_y

    app_state.historical_coords.append((ball_x, ball_y))
    if len(app_state.historical_coords) > settings.trail_length:
        app_state.historical_coords.pop(0)

    curr_weight = sum(smoothed.values())
    toolbar_visible = session_state.get("toolbar_visible", False)
    dpg.delete_item(dl, children_only=True)
    draw_main_screen(
        dl=dl,
        corners=corners,
        ball_x=ball_x,
        ball_y=ball_y,
        curr_weight=curr_weight,
        max_x=app_state.zoomed_max_x,
        max_y=app_state.zoomed_max_y,
        min_x=app_state.zoomed_min_x,
        min_y=app_state.zoomed_min_y,
        app_state=app_state,
        settings=settings,
        pan_offset_x=app_state.pan_offset_x,
        pan_offset_y=app_state.pan_offset_y,
        toolbar_visible=toolbar_visible,
    )

    if app_state.weight > 0:
        pl = (smoothed["top_left"] + smoothed["bottom_left"]) / app_state.weight
        pr = (smoothed["top_right"] + smoothed["bottom_right"]) / app_state.weight
    else:
        pl = pr = 0.5
    _update_stats_bar(pl, pr, curr_weight, app_state.weight)

    return top_left, top_right, bottom_left, bottom_right


def _handle_mouse_wheel(wheel_delta: float, app_state, session_state, settings) -> None:
    """
    Ctrl+Scroll: pan and zoomthe canvas so users can focus on off-centre regions.
    Plain scroll (no Ctrl): ignored here — reserved for future use.

    wheel_delta is computed by measuring dx and dy between mouse position and center of the screen
    scrolll up (away from user) is positive, scroll down (toward user) is negative. zooms in when scrolling up, out when scrolling down.
    """
    ctrl_held = dpg.is_key_down(dpg.mvKey_LControl)
    mouse_x, mouse_y = dpg.get_mouse_pos(local=False)
    if not ctrl_held:
        return  # plain scroll — do nothing

    # --- Mouse-anchored zoom ---
    # 1. Compute logical (content) coordinates under the mouse before zoom
    cx = app_state.screen_width // 2 + app_state.pan_offset_x
    cy = app_state.screen_height // 2 + app_state.pan_offset_y
    logical_x = (mouse_x - cx) / settings.zoom_factor
    logical_y = (mouse_y - cy) / settings.zoom_factor

    # 2. Compute new zoom factor
    try:
        slider_value = math.log(settings.zoom_factor) / math.log(ZOOM_SCALE)
    except (ValueError, ZeroDivisionError):
        slider_value = 0
    slider_value += wheel_delta * ZOOM_SPEED  # adjust by wheel delta
    slider_value = max(ZOOM_MIN, min(ZOOM_MAX, slider_value))
    new_zoom = ZOOM_SCALE**slider_value

    # 3. Update pan offset so the logical point under the mouse stays under the mouse
    new_pan_offset_x = mouse_x - (logical_x * new_zoom + app_state.screen_width // 2)
    new_pan_offset_y = mouse_y - (logical_y * new_zoom + app_state.screen_height // 2)
    app_state.pan_offset_x = new_pan_offset_x
    app_state.pan_offset_y = new_pan_offset_y

    dpg.set_value("zoom_slider", slider_value)
    _on_zoom_change(slider_value, settings, app_state)
    session_state["action"] = "pan_changed"


# ---------------------------------------------------------------------------
# Click handling — cursor toggle vs target circle
# ---------------------------------------------------------------------------


def _on_zoom_to_bbox(raw_max_x, raw_max_y, raw_min_x, raw_min_y, app_state, settings) -> None:
    """Auto-scale the viewport zoom so the cursor history fits the visible area."""
    bbox_w = max(abs(raw_max_x), abs(raw_min_x)) * 2
    bbox_h = max(abs(raw_max_y), abs(raw_min_y)) * 2
    base_w = app_state.screen_width * COORD_SCALE
    base_h = app_state.screen_height * COORD_SCALE
    if bbox_w < 1 or bbox_h < 1:
        return
    new_zoom = round(min(base_w / bbox_w, base_h / bbox_h), 10)
    new_zoom = max(ZOOM_MIN, min(ZOOM_MAX, new_zoom))
    settings.zoom_factor = new_zoom
    new_zoom = math.log(new_zoom) / math.log(ZOOM_SCALE)  # convert back to slider value
    dpg.set_value("zoom_slider", new_zoom)
    settings.save()


# Cached stats values — stats drawlist only redraws when these change.
# This eliminates the sub-pixel jitter that caused blurry text.
_stats_cache = {"left": -1, "weight": -1, "right": -1}


def _build_stats_bar(app_state) -> None:
    """Create or reset the overlay stats drawlist for the main screen."""
    # Create or reuse a dedicated drawlist for stats (bar + text).
    # front=True ensures it draws above the canvas drawlist.
    if not dpg.does_item_exist("stats_dl"):
        dpg.add_viewport_drawlist(tag="stats_dl", front=True)
    # Clear any content from a previous session
    dpg.delete_item("stats_dl", children_only=True)
    # Reset cache to force a full redraw on first frame
    _stats_cache["left"] = -1
    _stats_cache["weight"] = -1
    _stats_cache["right"] = -1


def _update_stats_bar(
    perc_left: float, perc_right: float, curr_weight: float, calib_weight: float
) -> None:
    """Draw the live left/right distribution and weight stats overlay."""
    left_val = int(perc_left * 100)
    weight_val = int(curr_weight)
    right_val = int(perc_right * 100)

    # Only redraw if values actually changed
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

    # Draw static background bar (light grey)
    dpg.draw_rectangle(
        (0, bar_top), (sw, bar_bot), fill=BAR_GREY_COLOR, color=BAR_GREY_COLOR, parent="stats_dl"
    )

    # Dynamic central stats bar color based on weight percentage
    percent = curr_weight / calib_weight if calib_weight > 0 else 0
    bar_color = get_stats_bar_color(percent)

    # Draw left/right distribution overlays as before
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

    # Text above the bar — bind crisp font so ImGui downscales the 100px atlas
    # glyph rather than upscaling the ~13px default bitmap font.
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


def _handle_canvas_click(mx: float, my: float, app_state, settings, session_state) -> None:
    """
    Left click on canvas: toggle cursor mode if clicking on cursor,
    otherwise add a target circle.
    Ignores clicks in the toolbar area.
    """
    if (
        (mx <= 50 and my <= 50)
        or (my <= TOOLBAR_FULL_H and session_state.get("toolbar_visible", False))
        or dpg.is_key_down(dpg.mvKey_LControl)
    ):  # Ctrl+Click is reserved for panning — ignore to prevent misclicks
        return
    cursor_radius = (
        int(CURSOR_HIT_FRACTION * app_state.screen_height)
        if settings.cursor_mode == "avatar"
        else CURSOR_HIT_RADIUS_CIRCLE
    )
    dist = math.sqrt((mx - app_state.ball_x) ** 2 + (my - app_state.ball_y) ** 2)
    if dist <= cursor_radius:
        settings.toggle_cursor_mode()
        if hasattr(app_state, "update_cursor_toggle_label"):
            app_state.update_cursor_toggle_label()
    else:
        # Start a new target-in-progress for drag-to-resize
        cx = app_state.screen_width // 2 + app_state.pan_offset_x
        cy = app_state.screen_height // 2 + app_state.pan_offset_y
        logical_x = (mx - cx) / settings.zoom_factor
        logical_y = (my - cy) / settings.zoom_factor
        app_state.target_in_progress = {
            "center": (logical_x, logical_y),
            "radius": 5.0,  # default initial radius in logical units
        }


def _handle_target_drag(app_state, settings):
    """Resize the target under construction while the mouse is dragged."""
    # Called on mouse drag if a target is being created
    if app_state.target_in_progress is None:
        return
    mouse_x, mouse_y = dpg.get_mouse_pos(local=False)
    cx = app_state.screen_width // 2 + app_state.pan_offset_x
    cy = app_state.screen_height // 2 + app_state.pan_offset_y
    logical_x = (mouse_x - cx) / settings.zoom_factor
    logical_y = (mouse_y - cy) / settings.zoom_factor
    x0, y0 = app_state.target_in_progress["center"]
    new_radius = math.sqrt((logical_x - x0) ** 2 + (logical_y - y0) ** 2)
    app_state.target_in_progress["radius"] = max(1.0, new_radius)


def _handle_target_release(app_state):
    """Finalize the current target when the mouse button is released."""
    # Called on mouse release to finalize target
    if app_state.target_in_progress is not None:
        app_state.clicked_locations.append(app_state.target_in_progress)
        app_state.target_in_progress = None


def _register_input_handlers(app_state, settings, session_state):
    """Register mouse interaction handlers for the main session canvas."""
    if dpg.does_item_exist("click_handler"):
        dpg.delete_item("click_handler")
    with dpg.handler_registry(tag="click_handler"):
        dpg.add_mouse_click_handler(
            button=0,
            callback=lambda: _handle_canvas_click(
                *dpg.get_mouse_pos(local=False),
                app_state,
                settings,
                session_state,
            ),
        )
        dpg.add_mouse_wheel_handler(
            callback=lambda s, v: _handle_mouse_wheel(v, app_state, session_state, settings),
        )
        dpg.add_mouse_drag_handler(
            button=0,
            threshold=0,
            callback=lambda s, d: (
                _handle_pan_drag(app_state, session_state)
                if dpg.is_key_down(dpg.mvKey_LControl)
                else _handle_target_drag(app_state, settings)
            ),
        )
        dpg.add_mouse_release_handler(
            button=0,
            callback=lambda: (
                _handle_pan_release(app_state)
                if getattr(app_state, "is_panning", False)
                else _handle_target_release(app_state)
            ),
        )


# --- Ctrl+Left Drag Pan Implementation ---
def _handle_pan_drag(app_state, session_state):
    """Handle Ctrl+drag panning of the main canvas."""
    import dearpygui.dearpygui as dpg

    # Only pan if Ctrl is held
    if not dpg.is_key_down(dpg.mvKey_LControl):
        return
    mouse_x, mouse_y = dpg.get_mouse_pos(local=False)
    if not getattr(app_state, "is_panning", False):
        # Start panning
        app_state.is_panning = True
        app_state.pan_start_mouse = (mouse_x, mouse_y)
        app_state.pan_start_offset = (app_state.pan_offset_x, app_state.pan_offset_y)
    else:
        start_x, start_y = app_state.pan_start_mouse
        offset_x, offset_y = app_state.pan_start_offset
        dx = mouse_x - start_x
        dy = mouse_y - start_y
        app_state.pan_offset_x = offset_x + dx
        app_state.pan_offset_y = offset_y + dy
        session_state["action"] = "pan_changed"


def _handle_pan_release(app_state):
    """Stop panning when the mouse button is released."""
    if getattr(app_state, "is_panning", False):
        app_state.is_panning = False


# ---------------------------------------------------------------------------
# Main run loop
# ---------------------------------------------------------------------------


def run(app_state, settings, args) -> None:
    """Outer loop — restarts session on RESTART, exits on QUIT."""
    while dpg.is_dearpygui_running():
        result = _run_session(app_state, settings, args)
        if result != 0:
            break


def _run_session(app_state, settings, args) -> int:
    """
    One full session: connect → tare → calibrate → main loop.
    Returns 0 to restart, 1 to quit.
    """
    app_state.reset()

    # Update screen dimensions from current viewport
    app_state.screen_width = dpg.get_viewport_width()
    # During connect/tare/calibration toolbar is hidden — use full height.
    # After calibration it shows, and resize handler corrects screen_height.
    app_state.screen_height = dpg.get_viewport_height()

    ensure_textures_loaded()

    # viewport_drawlist draws directly onto the viewport background (full screen)
    dl = dpg.add_viewport_drawlist(front=False)

    session_state = {"action": None, "toolbar_visible": False, "toolbar_enabled": False}

    # Clean up previous session widgets
    for _tag in ("control_panel", "gear_btn_window"):
        if dpg.does_item_exist(_tag):
            dpg.delete_item(_tag)

    _build_control_panel(app_state, settings, session_state)
    # Toolbar is created at startup but remains disabled until the main session
    # begins. Connection/calibration screens should not show settings controls.
    dpg.configure_item("control_panel", show=False)
    if dpg.does_item_exist("gear_btn_window"):
        dpg.configure_item("gear_btn_window", show=False)

    _build_stats_bar(app_state)

    _register_input_handlers(app_state, settings, session_state)

    device = _prepare_session(dl, app_state, settings, session_state, args)
    if device is None:
        return 1

    result = _run_main_loop(device, dl, app_state, settings, session_state)
    device.close()
    return result


def _run_main_loop(device, dl, app_state, settings, session_state) -> int:
    """Execute the main session render loop and return a session result."""
    # Extents now stored in app_state so zoom callback can rescale them live.
    # app_state.reset() already zeroes these — nothing else needed here.
    app_state.zoomed_max_x = app_state.zoomed_max_y = 0.0
    app_state.zoomed_min_x = app_state.zoomed_min_y = 0.0

    last_countdown_tick = time.time()
    record_start_time = None
    _last_frame_time = time.perf_counter()
    _TARGET_FRAME_S = 1.0 / 120  # cap at 120fps to avoid spinning
    # Corner values — initialised here so recording logic can reference them
    # even if the first data frame hasn't arrived yet.
    top_left = top_right = bottom_left = bottom_right = 0.0

    while dpg.is_dearpygui_running():
        now = time.time()
        record_start_time, last_countdown_tick = _update_countdown_and_recording(
            now,
            last_countdown_tick,
            record_start_time,
            app_state,
            settings,
            top_left,
            top_right,
            bottom_left,
            bottom_right,
        )
        _flush_record_buffer_if_complete(app_state)
        # Visual feedback overlays are now drawn in ui.draw_main_screen

        action = session_state.get("action")
        result = _handle_session_action(action, device, dl, app_state, settings, session_state)
        if result is not None:
            return result

        _handle_viewport_resize(app_state, session_state)

        top_left, top_right, bottom_left, bottom_right = _render_main_screen_frame(
            device,
            dl,
            app_state,
            settings,
            session_state,
            top_left,
            top_right,
            bottom_left,
            bottom_right,
        )

        dpg.render_dearpygui_frame()

        # Maintain frame cap — sleep any spare time so we don't spin at 1000fps.
        # This keeps CPU usage sane without adding input latency.
        now = time.perf_counter()
        elapsed = now - _last_frame_time
        if elapsed < _TARGET_FRAME_S:
            time.sleep(_TARGET_FRAME_S - elapsed)
        _last_frame_time = time.perf_counter()

    return 1
