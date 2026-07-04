"""WIIBBLE session lifecycle: connection, calibration, and main render loop."""

from __future__ import annotations

import contextlib
import datetime
import logging
import math
import time
from pathlib import Path

import dearpygui.dearpygui as dpg
import hid

import wiibble.ui.theme as _theme_module
from wiibble.board.acquisition import SensorAcquisition
from wiibble.board.mock_board import MockHIDDevice
from wiibble.board.recording import _save_recording_csv
from wiibble.features.data_processing import (
    apply_axis_flip,
    apply_filter,
    calculate_coordinates,
    calculate_force_deviation_kg,
    parse_data,
    tare,
)
from wiibble.session_report.launcher import (
    launch_session_report_async,
    parse_session_report_stdout,
)
from wiibble.ui.calibration_flow import (
    run_board_scale_calibration,
    run_board_weight_calibration,
    wait_for_tare,
)
from wiibble.ui.input import register_input_handlers
from wiibble.ui.theme import ICON_COG
from wiibble.ui.ui import (
    build_left_quick_access,
    build_panel_controls,
    build_panel_window,
    build_recording_quick_btn,
    build_stats_bar,
    collapse_settings_panel,
    draw_connection_failed_screen,
    draw_connection_screen,
    draw_main_screen,
    ensure_textures_loaded,
    set_quick_access_visible,
    set_stats_bar_visible,
    show_settings_panel,
    sync_recording_buttons,
    update_left_quick_access_layout,
    update_recording_quick_access_position,
    update_stats_bar,
)
from wiibble.utils.constants import (
    COORD_SCALE,
    DLL_RELATIVE_PATH,
    PRODUCT_ID,
    VENDOR_ID,
    ZOOM_MAX,
    ZOOM_MIN,
    ZOOM_SCALE,
)
from wiibble.utils.resources import resource_path

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Board connection
# ---------------------------------------------------------------------------


def connect_wii_board(
    use_mock: bool = False,
    mock_scenario: str = "sway",
    scale_factor: float | None = None,
):
    """Return an open HID device (real or mock)."""
    if use_mock:
        device = MockHIDDevice.from_scenario(mock_scenario)
        if scale_factor is not None:
            device.set_scale_factor(scale_factor)
        device.open(VENDOR_ID, PRODUCT_ID)
        log.info("Using MockHIDDevice (scenario: %s)", mock_scenario)
        return device
    try:
        log.info("Connecting to Wii Balance Board...")
        device = hid.device()
        device.open(VENDOR_ID, PRODUCT_ID)
        log.info("Connected successfully!")
        return device
    except OSError as e:
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

        from wiibble.board.board_connection import try_connection

        result = try_connection(resource_path(DLL_RELATIVE_PATH))
        if result == 0:
            return True

        # Show failed screen and wait for Enter key
        while dpg.is_dearpygui_running():
            dpg.delete_item(dl, children_only=True)
            draw_connection_failed_screen(dl, app_state)
            dpg.render_dearpygui_frame()
            if dpg.is_key_pressed(dpg.mvKey_Return):
                log.info("Connection retry requested (Enter)")
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
    if session_state.get("toolbar_visible", False):
        collapse_settings_panel(session_state, source="gear button")
    else:
        show_settings_panel(session_state, source="gear button")


def _collapse_ui_for_calibration(session_state: dict) -> bool:
    """Hide settings panel, quick-access controls, and stats bar during calibration."""
    was_visible = session_state.get("toolbar_visible", False)
    session_state["toolbar_visible"] = False
    if dpg.does_item_exist("control_panel"):
        dpg.configure_item("control_panel", show=False)
    set_quick_access_visible(False, session_state)
    set_stats_bar_visible(False)
    return was_visible


def _restore_ui_after_calibration(
    session_state: dict, was_toolbar_visible: bool
) -> None:
    """Restore settings panel and stats bar after calibration completes."""
    session_state["toolbar_visible"] = was_toolbar_visible
    toolbar_enabled = session_state.get("toolbar_enabled", False)
    if dpg.does_item_exist("control_panel"):
        dpg.configure_item("control_panel", show=was_toolbar_visible)
    if toolbar_enabled:
        update_left_quick_access_layout(was_toolbar_visible, toolbar_enabled)
        if dpg.does_item_exist("recording_quick_window"):
            dpg.configure_item("recording_quick_window", show=True)
    set_stats_bar_visible(True)


def _build_control_panel(app_state, settings, session_state: dict) -> None:
    """Build the left-side settings panel and canvas quick-access controls."""
    build_panel_window(
        app_state.screen_height,
        _get_gear_label(),
        lambda: _toggle_toolbar(session_state),
        lambda: build_panel_controls(app_state, settings, session_state),
    )
    build_left_quick_access(
        _get_gear_label(),
        lambda: _toggle_toolbar(session_state),
        session_state,
    )
    build_recording_quick_btn(app_state, settings)


def _recording_save_kwargs(app_state, settings) -> dict:
    """Build keyword args for _save_recording_csv from runtime state."""
    return {
        "prefix": settings.recording_prefix,
        "out_dir": settings.recording_dir,
        "flip_horizontal": settings.flip_horizontal,
        "flip_vertical": settings.flip_vertical,
        "start_time": (
            datetime.datetime.fromtimestamp(app_state.record_start)
            if app_state.record_start > 0
            else None
        ),
    }


def _on_recording_saved(csv_path: str, app_state, settings) -> None:
    """Toast after save and optionally launch end-of-session report generation."""
    app_state.last_recording_csv_path = csv_path
    if not settings.auto_report_after_recording:
        log.info("Recording saved (auto-report disabled)")
        app_state.toast_message = "Recording saved"
        app_state.toast_until = time.time() + 2.5
        return

    process = launch_session_report_async(
        csv_path,
        open_browser=settings.open_report_in_browser,
    )
    log.info("Auto-report triggered for %s", Path(csv_path).name)
    if process is None:
        app_state.toast_message = "Recording saved — report tool not found"
        app_state.toast_until = time.time() + 4.0
        return

    app_state.report_job = {"process": process, "csv_path": csv_path}
    app_state.toast_message = "Generating report..."
    app_state.toast_until = time.time() + 5.0


def _poll_report_job(app_state, settings) -> None:
    """Check async session-report subprocess; update toast when complete."""
    job = app_state.report_job
    if not job:
        return

    process = job["process"]
    if process.poll() is None:
        return

    app_state.report_job = None
    stdout, stderr = process.communicate()
    if process.returncode == 0:
        report_path = parse_session_report_stdout(stdout or "")
        if report_path and Path(report_path).is_file():
            app_state.last_report_path = report_path
        if settings.open_report_in_browser:
            app_state.toast_message = "Report ready — opened in browser"
        else:
            app_state.toast_message = "Report saved"
        app_state.toast_until = time.time() + 4.0
        log.info("Session report completed: %s", report_path or "(no path)")
        return

    log.error(
        "Session report failed for %s (exit %s): %s",
        job.get("csv_path"),
        process.returncode,
        (stderr or stdout or "").strip(),
    )
    app_state.toast_message = "Report generation failed"
    app_state.toast_until = time.time() + 4.0


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
        elapsed = now - (
            record_start_time if record_start_time else app_state.record_start
        )
        app_state.stopwatch_elapsed = elapsed
        # Always record raw (unfiltered) corner values so the UI filter
        # setting does not affect the posturographic analysis data.
        rc = app_state.raw_corners
        x_kg, y_kg = calculate_force_deviation_kg(
            rc["top_left"], rc["top_right"], rc["bottom_left"], rc["bottom_right"]
        )
        x_kg, y_kg = apply_axis_flip(
            x_kg, y_kg, settings.flip_horizontal, settings.flip_vertical
        )
        app_state.record_buffer.append((elapsed, x_kg, y_kg))
        if app_state.record_duration > 0 and elapsed >= app_state.record_duration:
            log.info(
                "Recording auto-stopped at duration limit (%ss)",
                app_state.record_duration,
            )
            app_state.is_recording = False
            app_state.recording_indicator = False
            app_state.stopwatch_elapsed = 0.0
            sync_recording_buttons(recording_active=False)
            csv_path = _save_recording_csv(
                app_state.record_buffer,
                app_state.weight,
                settings.filter_window,
                **_recording_save_kwargs(app_state, settings),
            )
            app_state.record_buffer = []
            _on_recording_saved(csv_path, app_state, settings)
    return record_start_time


def _flush_record_buffer_if_complete(app_state, settings=None) -> None:
    """Save the remaining recording buffer if recording has stopped."""
    if not app_state.is_recording and app_state.record_buffer:
        fw = settings.filter_window if settings is not None else 1
        rd = settings.recording_dir if settings is not None else ""
        csv_path = _save_recording_csv(
            app_state.record_buffer,
            app_state.weight,
            fw,
            flip_horizontal=settings.flip_horizontal if settings is not None else False,
            flip_vertical=settings.flip_vertical if settings is not None else False,
            prefix=settings.recording_prefix if settings is not None else "",
            out_dir=rd,
            start_time=(
                datetime.datetime.fromtimestamp(app_state.record_start)
                if app_state.record_start > 0
                else None
            ),
        )
        app_state.record_buffer = []
        app_state.recording_indicator = False
        app_state.stopwatch_elapsed = 0.0
        sync_recording_buttons(recording_active=False)
        if settings is not None:
            _on_recording_saved(csv_path, app_state, settings)
        else:
            app_state.toast_message = "Recording saved"
            app_state.toast_until = time.time() + 2.5


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
    if app_state.is_countdown and now - last_countdown_tick >= 1.0:
        app_state.countdown_value -= 1
        last_countdown_tick = now
        if app_state.countdown_value <= 0:
            app_state.is_countdown = False
            app_state.is_recording = True
            app_state.recording_indicator = True
            duration = app_state.record_duration
            label = "indefinite" if duration <= 0 else f"{duration}s"
            log.info("Recording started (duration=%s)", label)
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


def _handle_viewport_resize(app_state, settings, session_state):
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
    if toolbar_enabled:
        update_left_quick_access_layout(toolbar_currently_visible, toolbar_enabled)
        update_recording_quick_access_position(vw, settings.record_duration)
    # stats_dl redraws itself at correct position on next value change


def _clear_session_action(session_state):
    """Clear the current session action from shared state."""
    session_state["action"] = None
    session_state.pop("action_detail", None)


def _log_session_action(action: str, session_state: dict, message: str) -> None:
    """Log a session action, appending optional user-facing detail."""
    detail = session_state.pop("action_detail", None)
    if detail:
        log.info("%s (%s)", message, detail)
    else:
        log.info(message)


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
    app_state.reset_target_counter()


def _clear_screen_state(app_state, settings) -> None:
    """Clear targets and sway trail without touching pan or zoom."""
    app_state.clicked_locations = []
    app_state.target_in_progress = None
    app_state.target_move_in_progress = None
    app_state.historical_coords = [(0, 0)] * settings.trail_length
    app_state.zoomed_max_x = app_state.zoomed_max_y = 0.0
    app_state.zoomed_min_x = app_state.zoomed_min_y = 0.0
    app_state.raw_max_x = app_state.raw_max_y = 0.0
    app_state.raw_min_x = app_state.raw_min_y = 0.0


def _apply_zoom_to_bbox(app_state, settings) -> None:
    """Fit zoom and pan so the sway bounding box is centred and fully visible."""
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


def _pause_acquisition(session_state: dict) -> None:
    """Stop background HID reads so calibration owns the device exclusively."""
    acquisition = session_state.get("acquisition")
    if acquisition is not None:
        acquisition.stop()


def _resume_acquisition(session_state: dict) -> None:
    """Restart background HID reads after calibration completes."""
    acquisition = session_state.get("acquisition")
    if acquisition is not None:
        acquisition.start()


def _handle_session_action(action, device, dl, app_state, settings, session_state):
    """Process a toolbar action; return loop result if session restart needed."""
    if action == "restart":
        log.info("Session restart requested by user.")
        device.close()
        dpg.delete_item(dl)
        return 0
    if action == "reset":
        log.info("Session state reset")
        _reset_session_state(app_state, settings)
        _clear_session_action(session_state)
        return None
    if action == "clear":
        _log_session_action(action, session_state, "Targets and sway trail cleared")
        _clear_screen_state(app_state, settings)
        _clear_session_action(session_state)
        return None
    if action == "reset_target_counter":
        _log_session_action(action, session_state, "Target hit counter reset")
        app_state.reset_target_counter()
        _clear_session_action(session_state)
        return None
    if action == "zoom_to_bbox":
        _log_session_action(action, session_state, "Fit view to bounding box")
        _apply_zoom_to_bbox(app_state, settings)
        _clear_session_action(session_state)
        return None
    if action == "zoom_to_bbox_and_reset_pan":
        _log_session_action(
            action, session_state, "Fit view to bounding box (pan reset)"
        )
        _apply_zoom_to_bbox(app_state, settings)  # pan to bbox centre is handled inside
        _clear_session_action(session_state)
        return None
    if action == "pan_changed":
        _clear_session_action(session_state)
        return None
    if action == "calibrate":
        log.info("On-board weight calibration started")
        was_toolbar_visible = _collapse_ui_for_calibration(session_state)
        _pause_acquisition(session_state)
        try:
            weight = run_board_weight_calibration(
                device, dl, app_state, app_state.scale_factor
            )
            if weight > 0:
                settings.body_weight_kg = weight
                app_state.weight = weight
                settings.save()
                log.info("On-board weight calibration completed: %.1f kg", weight)
                if dpg.does_item_exist("body_weight_input"):
                    dpg.set_value("body_weight_input", weight)
        finally:
            _resume_acquisition(session_state)
            _restore_ui_after_calibration(session_state, was_toolbar_visible)
        _clear_session_action(session_state)
        return None
    if action == "calibrate_scale":
        ref_kg = settings.board_cal_reference_kg
        log.info("Board scale calibration started (reference=%.1f kg)", ref_kg)
        was_toolbar_visible = _collapse_ui_for_calibration(session_state)
        _pause_acquisition(session_state)
        try:
            new_factor = run_board_scale_calibration(
                device, dl, app_state, ref_kg, app_state.scale_factor
            )
            if new_factor > 0:
                settings.scale_factor = new_factor
                app_state.scale_factor = new_factor
                settings.save()
                log.info("Board scale calibration completed: factor=%.6f", new_factor)
                if hasattr(device, "set_scale_factor"):
                    device.set_scale_factor(new_factor)
        finally:
            _resume_acquisition(session_state)
            _restore_ui_after_calibration(session_state, was_toolbar_visible)
        _clear_session_action(session_state)
        return None
    if action == "toolbar_toggled":
        _clear_session_action(session_state)
        return None
    return None


def _prepare_session(dl, app_state, settings, session_state, args):
    """Run connection and tare startup steps before the main loop."""
    try:
        connected = _try_connection_loop(dl, app_state, use_mock=args.mock)
        if not connected:
            return None
    except Exception:
        log.exception("Connection failed")
        return None

    device = connect_wii_board(
        use_mock=args.mock,
        mock_scenario=args.mock_scenario,
        scale_factor=settings.scale_factor,
    )
    if not device:
        return None

    dpg.delete_item(dl, children_only=True)
    draw_connection_screen(dl, app_state)
    dpg.render_dearpygui_frame()

    app_state.scale_factor = settings.scale_factor
    wait_for_tare(device, dl, app_state, app_state.scale_factor)
    try:
        tare(device, app_state.data_struct)
    except Exception:
        log.exception("Failed to tare")
        device.close()
        return None

    app_state.weight = settings.body_weight_kg
    session_state["toolbar_enabled"] = True
    update_left_quick_access_layout(
        session_state.get("toolbar_visible", False),
        True,
    )
    if dpg.does_item_exist("recording_quick_window"):
        dpg.configure_item("recording_quick_window", show=True)
        update_recording_quick_access_position(
            dpg.get_viewport_width(), settings.record_duration
        )
    if hasattr(device, "enter_running_mode"):
        device.enter_running_mode()

    return device


def _render_main_screen_frame(
    acquisition,
    dl,
    app_state,
    settings,
    session_state,
    top_left: float,
    top_right: float,
    bottom_left: float,
    bottom_right: float,
    diagnostics: _LoopDiagnostics | None = None,
):
    """Render the main session frame when sensor data is available."""
    frame_state, reports_drained = _process_frame_data(
        acquisition,
        app_state,
        settings,
        top_left,
        top_right,
        bottom_left,
        bottom_right,
    )
    if diagnostics is not None:
        diagnostics.tick_frame(frame_state is not None, reports_drained)
    if frame_state is None:
        frame_state = session_state.get("last_frame")
        if frame_state is None:
            return top_left, top_right, bottom_left, bottom_right
    else:
        session_state["last_frame"] = frame_state

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
        toolbar_enabled=session_state.get("toolbar_enabled", False),
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
    acquisition,
    app_state,
    settings,
    top_left: float,
    top_right: float,
    bottom_left: float,
    bottom_right: float,
):
    """Read sensor data and update runtime cursor state for the current frame."""
    data, reports_drained = acquisition.drain_latest()
    if not data:
        return None, reports_drained

    corners = parse_data(data, app_state.data_struct, app_state.scale_factor)
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
    raw_x, raw_y = apply_axis_flip(
        raw_x, raw_y, settings.flip_horizontal, settings.flip_vertical
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
    }, reports_drained


# ---------------------------------------------------------------------------
# Click handling — cursor toggle vs target circle
# ---------------------------------------------------------------------------


def _on_zoom_to_bbox(
    raw_max_x, raw_max_y, raw_min_x, raw_min_y, app_state, settings
) -> None:
    """Scale zoom so the bounding box fits the visible area and centre the view."""
    bbox_w = raw_max_x - raw_min_x
    bbox_h = raw_max_y - raw_min_y
    base_w = app_state.screen_width * COORD_SCALE
    base_h = app_state.screen_height * COORD_SCALE
    if bbox_w < 1 or bbox_h < 1:
        return
    new_zoom = round(min(base_w / bbox_w, base_h / bbox_h), 10)
    new_zoom = max(ZOOM_MIN, min(ZOOM_MAX, new_zoom))
    settings.zoom_factor = new_zoom
    slider_value = math.log(new_zoom) / math.log(
        ZOOM_SCALE
    )  # convert back to slider value
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

# Approximate Wii Balance Board HID report interval (used for backlog lag estimate).
_HID_REPORT_INTERVAL_S = 0.01


class _LoopDiagnostics:
    """Aggregate main-loop timing and HID backlog metrics; log once per second."""

    LOG_INTERVAL_S = 1.0

    def __init__(self) -> None:
        self._window_start = time.perf_counter()
        self._frames = 0
        self._sensor_updates = 0
        self._empty_reads = 0
        self._max_reports_drained = 0
        self._sum_reports_drained = 0

    def tick_frame(self, had_sensor_data: bool, reports_drained: int) -> None:
        """Record one main-loop iteration."""
        self._frames += 1
        if had_sensor_data:
            self._sensor_updates += 1
            self._max_reports_drained = max(self._max_reports_drained, reports_drained)
            self._sum_reports_drained += reports_drained
        else:
            self._empty_reads += 1
        self._maybe_log()

    def _maybe_log(self) -> None:
        elapsed = time.perf_counter() - self._window_start
        if elapsed < self.LOG_INTERVAL_S:
            return
        fps = self._frames / elapsed
        sensor_hz = self._sensor_updates / elapsed
        avg_drained = (
            self._sum_reports_drained / self._sensor_updates
            if self._sensor_updates
            else 0.0
        )
        # If N reports were queued, the oldest would lag ~(N-1) report periods behind.
        est_backlog_lag_ms = (
            max(0, self._max_reports_drained - 1) * _HID_REPORT_INTERVAL_S * 1000
        )
        log.debug(
            "Loop perf: fps=%.1f sensor_hz=%.1f empty_reads=%d "
            "max_hid_batch=%d avg_hid_batch=%.1f est_backlog_lag_ms=%.0f",
            fps,
            sensor_hz,
            self._empty_reads,
            self._max_reports_drained,
            avg_drained,
            est_backlog_lag_ms,
        )
        if self._max_reports_drained >= 3:
            log.warning(
                "HID backlog: up to %d reports drained in one frame "
                "(~%.0f ms stale if only oldest had been used); "
                "render loop may be slower than board ~100 Hz",
                self._max_reports_drained,
                est_backlog_lag_ms,
            )
        self._window_start = time.perf_counter()
        self._frames = 0
        self._sensor_updates = 0
        self._empty_reads = 0
        self._max_reports_drained = 0
        self._sum_reports_drained = 0


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
    One full session: connect → tare → main loop.
    Returns 0 to restart, 1 to quit.
    """
    log.info(
        "Session starting (mock=%s, scenario=%s).",
        args.mock,
        getattr(args, "mock_scenario", "n/a"),
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
    for _tag in ("control_panel", "left_quick_access_window", "recording_quick_window"):
        if dpg.does_item_exist(_tag):
            dpg.delete_item(_tag)

    _build_control_panel(app_state, settings, session_state)
    # Panel is created at startup but remains hidden until the main session
    # begins. Connection/calibration screens should not show settings controls.
    dpg.configure_item("control_panel", show=False)
    set_quick_access_visible(False, session_state)

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
    with contextlib.suppress(Exception):
        device.set_nonblocking(1)

    acquisition = SensorAcquisition(device)
    acquisition.start()
    session_state["acquisition"] = acquisition

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
    diagnostics = _LoopDiagnostics()

    try:
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
            _poll_report_job(app_state, settings)

            action = session_state.get("action")
            result = _handle_session_action(
                action, device, dl, app_state, settings, session_state
            )
            if result is not None:
                return result

            _handle_viewport_resize(app_state, settings, session_state)

            top_left, top_right, bottom_left, bottom_right = _render_main_screen_frame(
                acquisition,
                dl,
                app_state,
                settings,
                session_state,
                top_left,
                top_right,
                bottom_left,
                bottom_right,
                diagnostics=diagnostics,
            )

            dpg.render_dearpygui_frame()

            now = time.perf_counter()
            elapsed = now - _last_frame_time
            if elapsed < _TARGET_FRAME_S:
                time.sleep(_TARGET_FRAME_S - elapsed)
            _last_frame_time = time.perf_counter()
    finally:
        acquisition.stop()
        session_state.pop("acquisition", None)

    return 1
