"""WIIBBLE application runtime.

This module contains the main session lifecycle, device connection flow,
DearPyGui UI glue code, and the primary render + recording loop.
"""

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
    DLL_RELATIVE_PATH,
    PRODUCT_ID,
    VENDOR_ID,
    ZOOM_MAX,
    ZOOM_MIN,
    ZOOM_SCALE,
)
from data_processing import (
    apply_filter,
    calculate_coordinates,
    calculate_force_deviation_kg,
    parse_data,
    read_data,
    tare,
)
from input import register_input_handlers
from mock_board import MockHIDDevice
from recording import _save_recording_csv
from resources import resource_path
from theme import ICON_COG
from ui import (
    build_panel_controls,
    build_panel_toggle_btn,
    build_panel_window,
    build_stats_bar,
    draw_connection_failed_screen,
    draw_connection_screen,
    draw_main_screen,
    ensure_textures_loaded,
    update_stats_bar,
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
    """Toggle the settings panel visibility state for the session."""
    visible = not session_state.get("toolbar_visible", False)
    session_state["toolbar_visible"] = visible
    if visible:
        # Show full panel, hide floating toggle button
        if dpg.does_item_exist("control_panel"):
            dpg.configure_item("control_panel", show=True)
        if dpg.does_item_exist("panel_toggle_window"):
            dpg.configure_item("panel_toggle_window", show=False)
    else:
        # Hide panel, show floating toggle button
        if dpg.does_item_exist("control_panel"):
            dpg.configure_item("control_panel", show=False)
        if dpg.does_item_exist("panel_toggle_window"):
            dpg.configure_item("panel_toggle_window", show=True)
    session_state["action"] = "toolbar_toggled"


def _build_control_panel(app_state, settings, session_state: dict) -> None:
    """Build the left-side settings panel and the collapsed floating toggle button."""
    build_panel_window(
        app_state.screen_height,
        _get_gear_label(),
        lambda: _toggle_toolbar(session_state),
        lambda: build_panel_controls(app_state, settings, session_state),
    )
    build_panel_toggle_btn(
        _get_gear_label(),
        lambda: _toggle_toolbar(session_state),
    )


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
        # Always record raw (unfiltered) corner values so the UI filter
        # setting does not affect the posturographic analysis data.
        rc = app_state.raw_corners
        x_kg, y_kg = calculate_force_deviation_kg(
            rc["top_left"], rc["top_right"], rc["bottom_left"], rc["bottom_right"]
        )
        app_state.record_buffer.append((elapsed, x_kg, y_kg))
        if app_state.record_duration > 0 and elapsed >= app_state.record_duration:
            app_state.is_recording = False
            app_state.recording_indicator = False
            app_state.stopwatch_elapsed = 0.0
            dpg.set_item_label("start_recording_btn", "Start Recording")
            _save_recording_csv(app_state.record_buffer, app_state.weight, settings.filter_window)
            app_state.record_buffer = []
    return record_start_time


def _flush_record_buffer_if_complete(app_state, settings=None) -> None:
    """Save the remaining recording buffer if recording has stopped."""
    if not app_state.is_recording and app_state.record_buffer:
        fw = settings.filter_window if settings is not None else 1
        _save_recording_csv(app_state.record_buffer, app_state.weight, fw)
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
    """Update app dimensions and panel height on viewport resize."""
    vw = dpg.get_viewport_width()
    vh = dpg.get_viewport_height()
    if vw == app_state.screen_width and vh == app_state.screen_height:
        return

    app_state.screen_width = vw
    app_state.screen_height = vh
    toolbar_currently_visible = session_state.get("toolbar_visible", False)
    toolbar_enabled = session_state.get("toolbar_enabled", False)
    dpg.configure_item("control_panel", height=vh, show=toolbar_currently_visible)
    if dpg.does_item_exist("panel_toggle_window"):
        dpg.configure_item(
            "panel_toggle_window",
            show=toolbar_enabled and not toolbar_currently_visible,
        )
    # stats_dl redraws itself at correct position on next value change


def _clear_session_action(session_state):
    """Clear the current session action from shared state."""
    session_state["action"] = None


def _reset_session_state(app_state, settings) -> None:
    """Reset runtime session state after a toolbar reset action."""
    app_state.clicked_locations = []
    app_state.historical_coords = [(0, 0)] * settings.trail_length
    app_state.zoomed_max_x = app_state.zoomed_max_y = 0.0
    app_state.zoomed_min_x = app_state.zoomed_min_y = 0.0
    app_state.raw_max_x = app_state.raw_max_y = 0.0
    app_state.raw_min_x = app_state.raw_min_y = 0.0
    app_state.pan_offset_x = 0.0
    app_state.pan_offset_y = 0.0


def _clear_screen_state(app_state, settings) -> None:
    """Clear targets and sway trail without touching pan or zoom."""
    app_state.clicked_locations = []
    app_state.historical_coords = [(0, 0)] * settings.trail_length
    app_state.zoomed_max_x = app_state.zoomed_max_y = 0.0
    app_state.zoomed_min_x = app_state.zoomed_min_y = 0.0
    app_state.raw_max_x = app_state.raw_max_y = 0.0
    app_state.raw_min_x = app_state.raw_min_y = 0.0


def _apply_zoom_to_bbox(app_state, settings) -> None:
    """Fit zoom and pan so the recorded sway bounding box is centred and fully visible."""
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


def _reset_pan(app_state) -> None:
    """Reset the current canvas pan offsets to the default centered position."""
    app_state.pan_offset_x = 0.0
    app_state.pan_offset_y = 0.0


def _handle_session_action(action, device, dl, app_state, settings, session_state):
    """Process a toolbar action request and return a loop result if a session restart is needed."""
    if action == "restart":
        log.info("Session restart requested by user.")
        device.close()
        dpg.delete_item(dl)
        return 0
    if action == "reset":
        _reset_session_state(app_state, settings)
        _clear_session_action(session_state)
        return None
    if action == "clear":
        _clear_screen_state(app_state, settings)
        _clear_session_action(session_state)
        return None
    if action == "zoom_to_bbox":
        _apply_zoom_to_bbox(app_state, settings)
        _clear_session_action(session_state)
        return None
    if action == "zoom_to_bbox_and_reset_pan":
        _apply_zoom_to_bbox(app_state, settings)  # pan to bbox centre is handled inside
        _clear_session_action(session_state)
        return None
    if action == "pan_changed":
        _clear_session_action(session_state)
        return None
    if action == "toolbar_toggled":
        _clear_session_action(session_state)
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
        log.warning("Calibration aborted — window closed before subject stepped on.")
        device.close()
        return None

    app_state.weight = calibrated_weight
    session_state["toolbar_enabled"] = True
    if dpg.does_item_exist("panel_toggle_window"):
        dpg.configure_item("panel_toggle_window", show=True)

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
    """Render the main session frame when sensor data is available."""
    frame_state = _process_frame_data(
        device,
        app_state,
        settings,
        top_left,
        top_right,
        bottom_left,
        bottom_right,
    )
    if frame_state is None:
        return top_left, top_right, bottom_left, bottom_right

    dpg.delete_item(dl, children_only=True)
    draw_main_screen(
        dl=dl,
        corners=frame_state["corners"],
        ball_x=frame_state["ball_x"],
        ball_y=frame_state["ball_y"],
        curr_weight=frame_state["curr_weight"],
        max_x=app_state.zoomed_max_x,
        max_y=app_state.zoomed_max_y,
        min_x=app_state.zoomed_min_x,
        min_y=app_state.zoomed_min_y,
        app_state=app_state,
        settings=settings,
        pan_offset_x=app_state.pan_offset_x,
        pan_offset_y=app_state.pan_offset_y,
        toolbar_visible=session_state.get("toolbar_visible", False),
    )

    update_stats_bar(
        frame_state["pl"],
        frame_state["pr"],
        frame_state["curr_weight"],
        app_state.weight,
    )

    return (
        frame_state["top_left"],
        frame_state["top_right"],
        frame_state["bottom_left"],
        frame_state["bottom_right"],
    )


def _process_frame_data(
    device,
    app_state,
    settings,
    top_left: float,
    top_right: float,
    bottom_left: float,
    bottom_right: float,
):
    """Read sensor data and update runtime cursor state for the current frame."""
    data = read_data(device)
    if not data:
        return None

    corners = parse_data(data, app_state.data_struct)
    app_state.raw_corners = corners  # store unfiltered values for recording
    smoothed = apply_filter(corners, app_state.filter_buffer, settings.filter_window)
    top_right = smoothed["top_right"]
    bottom_right = smoothed["bottom_right"]
    top_left = smoothed["top_left"]
    bottom_left = smoothed["bottom_left"]

    raw_x, raw_y = calculate_coordinates(
        top_left,
        top_right,
        bottom_left,
        bottom_right,
        weight=app_state.weight,
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
    if app_state.weight > 0:
        pl = (smoothed["top_left"] + smoothed["bottom_left"]) / app_state.weight
        pr = (smoothed["top_right"] + smoothed["bottom_right"]) / app_state.weight
    else:
        pl = pr = 0.5

    return {
        "corners": corners,
        "ball_x": ball_x,
        "ball_y": ball_y,
        "curr_weight": curr_weight,
        "pl": pl,
        "pr": pr,
        "top_left": top_left,
        "top_right": top_right,
        "bottom_left": bottom_left,
        "bottom_right": bottom_right,
    }


# ---------------------------------------------------------------------------
# Click handling — cursor toggle vs target circle
# ---------------------------------------------------------------------------


def _on_zoom_to_bbox(raw_max_x, raw_max_y, raw_min_x, raw_min_y, app_state, settings) -> None:
    """Scale zoom so the actual bounding box fits the visible area and centre the view on it."""
    bbox_w = raw_max_x - raw_min_x
    bbox_h = raw_max_y - raw_min_y
    base_w = app_state.screen_width * COORD_SCALE
    base_h = app_state.screen_height * COORD_SCALE
    if bbox_w < 1 or bbox_h < 1:
        return
    new_zoom = round(min(base_w / bbox_w, base_h / bbox_h), 10)
    new_zoom = max(ZOOM_MIN, min(ZOOM_MAX, new_zoom))
    settings.zoom_factor = new_zoom
    slider_value = math.log(new_zoom) / math.log(ZOOM_SCALE)  # convert back to slider value
    dpg.set_value("zoom_slider", slider_value)
    settings.save()
    # Pan so the bbox centre sits at the screen centre
    cx_raw = (raw_max_x + raw_min_x) / 2
    cy_raw = (raw_max_y + raw_min_y) / 2
    app_state.pan_offset_x = -cx_raw * new_zoom
    app_state.pan_offset_y = -cy_raw * new_zoom


# Cached stats values — stats drawlist only redraws when these change.
# This eliminates the sub-pixel jitter that caused blurry text.
_stats_cache = {"left": -1, "weight": -1, "right": -1}


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
    log.info(
        "Session starting (mock=%s, scenario=%s).", args.mock, getattr(args, "mock_scenario", "n/a")
    )
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
    for _tag in ("control_panel", "panel_toggle_window"):
        if dpg.does_item_exist(_tag):
            dpg.delete_item(_tag)

    _build_control_panel(app_state, settings, session_state)
    # Panel is created at startup but remains hidden until the main session
    # begins. Connection/calibration screens should not show settings controls.
    dpg.configure_item("control_panel", show=False)
    if dpg.does_item_exist("panel_toggle_window"):
        dpg.configure_item("panel_toggle_window", show=False)

    build_stats_bar(app_state)

    register_input_handlers(app_state, settings, session_state)

    device = _prepare_session(dl, app_state, settings, session_state, args)
    if device is None:
        return 1

    result = _run_main_loop(device, dl, app_state, settings, session_state)
    device.close()
    log.info("Session ended (result=%s).", "restart" if result == 0 else "quit")
    return result


def _run_main_loop(device, dl, app_state, settings, session_state) -> int:
    """Execute the main session render loop and return a session result."""
    # Extents now stored in app_state so zoom callback can rescale them live.
    # app_state.reset() already zeroes these — nothing else needed here.
    app_state.zoomed_max_x = app_state.zoomed_max_y = 0.0
    app_state.zoomed_min_x = app_state.zoomed_min_y = 0.0

    try:
        device.set_nonblocking(1)
    except Exception:
        pass

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
        _flush_record_buffer_if_complete(app_state, settings)
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
