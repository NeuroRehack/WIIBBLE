"""Settings panel controls for the WIIBBLE overlay window."""

from __future__ import annotations

import logging
import os
import platform
import subprocess
import time
from datetime import datetime
from pathlib import Path

import dearpygui.dearpygui as dpg

import wiibble.ui.theme as _theme_module
from wiibble.features.sts_counter import format_sts_state_label, weight_pct_of_body
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
    apply_sts_min_dwell_seconds,
    apply_sts_sit_threshold_pct,
    apply_sts_stand_threshold_pct,
    apply_target_dwell_seconds,
    apply_thrive_broker_host,
    apply_thrive_hub_id,
    apply_trail_length,
    apply_zoom_slider,
    request_calibrate_board,
    request_calibrate_scale,
    toggle_cursor_mode,
    toggle_recording,
)
from wiibble.session_report.launcher import open_report_in_browser
from wiibble.ui.theme import (
    ICON_FLIP_HORIZONTAL,
    ICON_FLIP_VERTICAL,
    ICON_INFINITY,
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
    STS_MIN_DWELL_MAX,
    STS_MIN_DWELL_MIN,
    STS_MIN_DWELL_STEP,
    STS_SIT_THRESHOLD_PCT_MAX,
    STS_SIT_THRESHOLD_PCT_MIN,
    STS_STAND_THRESHOLD_PCT_MAX,
    STS_STAND_THRESHOLD_PCT_MIN,
    TARGET_DWELL_MAX,
    TARGET_DWELL_MIN,
    TARGET_DWELL_STEP,
    ZOOM_MAX,
    ZOOM_MIN,
)
from wiibble.utils.recording_names import (
    DEFAULT_RECORDING_DIR,
    normalize_recording_prefix,
    report_search_paths,
    resolve_recording_dir,
)

log = logging.getLogger(__name__)

_trail_active_theme = None

# Duration preset values (seconds); 0 = indefinite
_DURATION_PRESETS = [
    (10, "10s"),
    (20, "20s"),
    (30, "30s"),
    (60, "60s"),
    (0, ICON_INFINITY),
]


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


def _cursor_label(settings) -> str:
    """Return what the cursor toggle button will switch TO (action label)."""
    return (
        "Switch to Avatar" if settings.cursor_mode == "circle" else "Switch to Circle"
    )


def update_cursor_toggle_label(settings) -> None:
    """Update the panel cursor button label to reflect the current mode."""
    if dpg.does_item_exist("cursor_toggle_btn"):
        dpg.set_item_label("cursor_toggle_btn", _cursor_label(settings))


def _on_cursor_toggle(settings) -> None:
    """Toggle the cursor display mode and update the panel label."""
    toggle_cursor_mode(settings)
    update_cursor_toggle_label(settings)


def _on_cursor_size_change(value: int, settings) -> None:
    """Persist a new cursor size selection and update settings."""
    apply_cursor_size(settings, value)


def _on_record_duration_change(value: int, settings, app_state) -> None:
    """Persist a new recording duration selection in settings and runtime state."""
    apply_record_duration(settings, app_state, value)
    from wiibble.ui.ui import update_recording_quick_access_position

    update_recording_quick_access_position(dpg.get_viewport_width(), value)


def _on_start_recording(app_state, settings, *, source: str = "panel") -> None:
    """Start or stop a recording session from the controls toolbar."""
    active = toggle_recording(app_state, settings, source=source)
    from wiibble.ui.ui import sync_recording_buttons

    sync_recording_buttons(recording_active=active)


def _on_body_weight_change(value: float, settings, app_state) -> None:
    """Persist a manual body weight and sync it to runtime state."""
    clamped = apply_body_weight(settings, app_state, value)
    if clamped is not None and dpg.does_item_exist("body_weight_input"):
        dpg.set_value("body_weight_input", clamped)


def _relative_tare_label(saved_at: datetime, *, now: datetime | None = None) -> str:
    """
    Format a tare timestamp as a relative label for the settings panel.

    Args:
        saved_at: When tare was last persisted (timezone-aware or naive).
        now: Reference time for tests; defaults to current local time.

    Returns:
        Human-readable relative string, e.g. "just now" or "5 min ago".
    """
    if saved_at.tzinfo is not None:
        saved_local = saved_at.astimezone()
        if now is None:
            reference = datetime.now(saved_local.tzinfo)
        elif now.tzinfo is not None:
            reference = now.astimezone()
        else:
            reference = now.replace(tzinfo=saved_local.tzinfo)
    else:
        saved_local = saved_at
        reference = now if now is not None else datetime.now()

    age_seconds = max(0, int((reference - saved_local).total_seconds()))
    if age_seconds < 60:
        return "just now"
    if age_seconds < 3600:
        return f"{age_seconds // 60} min ago"
    if age_seconds < 86400:
        return f"{age_seconds // 3600} hr ago"
    return saved_local.strftime("%Y-%m-%d %H:%M")


def _format_tare_status(settings) -> str:
    """Return a short label for the persisted tare timestamp."""
    if not settings.has_saved_tare():
        return "Tare: not saved"
    try:
        saved_at = datetime.fromisoformat(settings.tare_saved_at)
        return f"Tare saved: {_relative_tare_label(saved_at)}"
    except ValueError:
        return f"Tare saved: {settings.tare_saved_at}"


def update_tare_status_label(settings) -> None:
    """Refresh the calibration panel tare timestamp label."""
    if not dpg.does_item_exist("tare_status_label"):
        return
    dpg.set_value("tare_status_label", _format_tare_status(settings))


def _on_calibrate_board(session_state: dict) -> None:
    """Request on-board weight calibration from the main loop."""
    log.info("On-board weight calibration requested")
    request_calibrate_board(session_state)


def _on_board_cal_reference_change(value: float, settings) -> None:
    """Persist the reference mass used for board scale calibration."""
    clamped = apply_board_cal_reference(settings, value)
    if clamped is not None and dpg.does_item_exist("board_cal_reference_input"):
        dpg.set_value("board_cal_reference_input", clamped)


def _on_calibrate_scale(session_state: dict) -> None:
    """Request board scale-factor calibration from the main loop."""
    log.info("Board scale calibration requested")
    request_calibrate_scale(session_state)


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
            "Step off, tare the board, then step on to measure body weight.\n"
            "Also refreshes the saved zero baseline when complete."
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
    dpg.add_spacer(height=8)
    dpg.add_text(_format_tare_status(settings), tag="tare_status_label")


def _open_folder_in_file_manager(path: Path) -> None:
    """Open a folder in the system file manager."""
    folder = path.resolve()
    try:
        system = platform.system()
        if system == "Windows":
            os.startfile(folder)  # noqa: S606
        elif system == "Darwin":
            subprocess.run(["open", str(folder)], check=False)
        else:
            subprocess.run(["xdg-open", str(folder)], check=False)
        log.info("Opened recording folder: %s", folder)
    except OSError as exc:
        log.warning("Could not open recording folder %s: %s", folder, exc)


def _on_open_recording_folder(settings) -> None:
    """Open the configured recordings folder in the system file manager."""
    folder = resolve_recording_dir(settings.recording_dir)
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        log.warning("Could not create recording folder %s: %s", folder, exc)
        return
    _open_folder_in_file_manager(folder)


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

        def _on_dir_picker_cancel(sender, app_data) -> None:
            log.info("Recording folder picker cancelled")
            dpg.hide_item("recording_dir_dialog")

        dpg.add_file_dialog(
            directory_selector=True,
            show=False,
            tag="recording_dir_dialog",
            width=700,  # wider for more margin
            height=400,
            default_path=initial,
            callback=_on_dir_picker,
            cancel_callback=_on_dir_picker_cancel,
            modal=True,
        )
        dpg.bind_item_theme("recording_dir_dialog", "recording_dir_dialog_theme")
    dpg.show_item("recording_dir_dialog")
    log.info("Recording folder picker opened")


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


def sync_report_progress_ui(app_state) -> None:
    """Show or hide the session-report progress widgets in the settings panel."""
    if not dpg.does_item_exist("report_progress_group"):
        return

    active = app_state.report_job is not None
    dpg.configure_item("report_progress_group", show=active)
    if not active:
        if dpg.does_item_exist("report_progress_bar"):
            dpg.set_value("report_progress_bar", 0.0)
            dpg.configure_item("report_progress_bar", overlay="")
        return

    progress = getattr(app_state, "report_progress", None) or {}
    label = progress.get("label") or "Generating report..."
    step = int(progress.get("step", 0))
    total = max(1, int(progress.get("total", 1)))
    pct = float(progress.get("pct", 0.0))

    if dpg.does_item_exist("report_progress_label"):
        dpg.set_value("report_progress_label", label)
    if dpg.does_item_exist("report_progress_bar"):
        dpg.set_value("report_progress_bar", pct)
        dpg.configure_item(
            "report_progress_bar",
            overlay=f"{step}/{total}",
        )


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
        log.info("Opened last report: %s", report_path.name)
        return

    log.info("View last report — none available")
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
    if not dpg.does_item_exist("recording_dir_click_handler"):
        with dpg.item_handler_registry(tag="recording_dir_click_handler"):
            dpg.add_item_clicked_handler(
                callback=lambda s, a: _on_open_recording_folder(settings)
            )
    dpg.add_text(_display_dir, tag="recording_dir_label", wrap=PANEL_BTN_W)
    dpg.bind_item_handler_registry("recording_dir_label", "recording_dir_click_handler")
    with dpg.theme() as _recording_dir_link_theme, dpg.theme_component(dpg.mvText):
        dpg.add_theme_color(
            dpg.mvThemeCol_Text,
            _theme_module.C_BRAND,
            category=dpg.mvThemeCat_Core,
        )
    dpg.bind_item_theme("recording_dir_label", _recording_dir_link_theme)
    with dpg.tooltip(parent="recording_dir_label"):
        dpg.add_text("Click to open this folder in your file manager.")
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
            "Filename prefix for recordings, metrics JSON, and reports "
            "(max 40 characters).\n"
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
    with dpg.group(tag="report_progress_group", horizontal=True, show=False):
        dpg.add_loading_indicator(tag="report_progress_spinner", style=1, radius=1.0)
        with dpg.group():
            dpg.add_text("Generating report...", tag="report_progress_label")
            dpg.add_progress_bar(
                tag="report_progress_bar",
                default_value=0.0,
                overlay="",
                width=PANEL_BTN_W - 32,
            )
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


def _build_thrive_controls(settings) -> None:
    """Add THRIVE hub MQTT export settings."""
    dpg.add_spacer(height=8)
    dpg.add_text("THRIVE export")
    dpg.add_checkbox(
        tag="thrive_enabled_cb",
        label="Export to THRIVE hub",
        default_value=settings.thrive_enabled,
        callback=lambda s, v: _on_thrive_enabled_change(v, settings),
    )
    with dpg.tooltip(parent="thrive_enabled_cb"):
        dpg.add_text(
            "Publish live balance-board data to a THRIVE rehabilitation hub\n"
            "over MQTT while WIIBBLE is running.\n"
            "Requires the THRIVE companion process and network access\n"
            "to the hub PC (port 1883)."
        )
    dpg.add_spacer(height=4)
    dpg.add_text("Broker host")
    dpg.add_input_text(
        tag="thrive_broker_host_input",
        default_value=settings.thrive_broker_host,
        width=PANEL_BTN_W,
        callback=lambda s, v: _on_thrive_broker_host_change(v, settings),
    )
    with dpg.tooltip(parent="thrive_broker_host_input"):
        dpg.add_text(
            "LAN IP address of the THRIVE PC running Mosquitto.\n"
            "Use localhost only when the hub is on this machine."
        )
    dpg.add_spacer(height=4)
    dpg.add_text("Hub ID")
    dpg.add_input_text(
        tag="thrive_hub_id_input",
        default_value=settings.thrive_hub_id,
        width=PANEL_BTN_W,
        callback=lambda s, v: _on_thrive_hub_id_change(v, settings),
    )
    with dpg.tooltip(parent="thrive_hub_id_input"):
        dpg.add_text(
            "Must match HUB_ID in the THRIVE .env file (default: demo).\n"
            "MQTT topics use thrive/{hub_id}/nodes/wiibble_01/..."
        )


def _on_thrive_enabled_change(value: bool, settings) -> None:
    apply_setting_bool(settings, "thrive_enabled", value)


def _on_thrive_broker_host_change(value: str, settings) -> None:
    apply_thrive_broker_host(settings, value)


def _on_thrive_hub_id_change(value: str, settings) -> None:
    apply_thrive_hub_id(settings, value)


def _build_cursor_controls(app_state, settings) -> None:
    """Add cursor mode toggle, size, trail, and smoothing filter to the panel."""
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
            "Size slider and on-screen drag resize apply to both."
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
            "Adjust the cursor size.\nYou can also drag the cursor on screen to resize."
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
        callback=lambda: session_state.update(
            {"action": "zoom_to_bbox_and_reset_pan", "action_detail": "panel"}
        ),
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
        callback=lambda: session_state.update(
            {"action": "reset_target_counter", "action_detail": "panel"}
        ),
        width=PANEL_BTN_W,
        height=PANEL_BTN_H,
    )
    with dpg.tooltip(parent="reset_target_counter_btn"):
        dpg.add_text("Reset target hit and sit-to-stand rep counters to zero.")
    dpg.add_spacer(height=8)
    dpg.add_text("Sit-to-stand counter")
    dpg.add_checkbox(
        tag="sts_enabled_checkbox",
        label="Enable STS rep counter",
        default_value=settings.sts_enabled,
        callback=lambda s, v: _on_sts_enabled_change(v, settings),
    )
    with dpg.tooltip(parent="sts_enabled_checkbox"):
        dpg.add_text(
            "Count sit-to-stand reps from total weight.\n"
            "Requires calibrated body weight."
        )
    dpg.add_spacer(height=4)
    dpg.add_checkbox(
        tag="sts_show_counter_checkbox",
        label="Show STS rep counter",
        default_value=settings.sts_show_counter,
        callback=lambda s, v: _on_sts_show_counter_change(v, settings),
    )
    with dpg.tooltip(parent="sts_show_counter_checkbox"):
        dpg.add_text("Show or hide the on-screen STS rep counter.")
    dpg.add_spacer(height=4)
    dpg.add_text("Stand threshold (% body weight)")
    dpg.add_input_float(
        tag="sts_stand_threshold_input",
        default_value=settings.sts_stand_threshold_pct,
        min_value=STS_STAND_THRESHOLD_PCT_MIN,
        max_value=STS_STAND_THRESHOLD_PCT_MAX,
        step=1.0,
        format="%.1f",
        width=PANEL_BTN_W,
        callback=lambda s, v: _on_sts_stand_threshold_change(v, settings),
    )
    with dpg.tooltip(parent="sts_stand_threshold_input"):
        dpg.add_text(
            "Weight must reach this fraction of body weight\n"
            "and hold for the min stand time to count a rep."
        )
    dpg.add_spacer(height=4)
    dpg.add_text("Sit threshold (% body weight)")
    dpg.add_input_float(
        tag="sts_sit_threshold_input",
        default_value=settings.sts_sit_threshold_pct,
        min_value=STS_SIT_THRESHOLD_PCT_MIN,
        max_value=STS_SIT_THRESHOLD_PCT_MAX,
        step=1.0,
        format="%.1f",
        width=PANEL_BTN_W,
        callback=lambda s, v: _on_sts_sit_threshold_change(v, settings),
    )
    with dpg.tooltip(parent="sts_sit_threshold_input"):
        dpg.add_text(
            "Weight must drop to this fraction of body weight\n"
            "and hold for the min sit time to complete a rep."
        )
    dpg.add_spacer(height=4)
    dpg.add_text("Min stand time (s)")
    dpg.add_input_float(
        tag="sts_min_stand_input",
        default_value=settings.sts_min_stand_seconds,
        min_value=STS_MIN_DWELL_MIN,
        max_value=STS_MIN_DWELL_MAX,
        step=STS_MIN_DWELL_STEP,
        format="%.1f",
        width=PANEL_BTN_W,
        callback=lambda s, v: _on_sts_min_stand_change(v, settings),
    )
    with dpg.tooltip(parent="sts_min_stand_input"):
        dpg.add_text("Seconds above the stand threshold before standing is confirmed.")
    dpg.add_spacer(height=4)
    dpg.add_text("Min sit time (s)")
    dpg.add_input_float(
        tag="sts_min_sit_input",
        default_value=settings.sts_min_sit_seconds,
        min_value=STS_MIN_DWELL_MIN,
        max_value=STS_MIN_DWELL_MAX,
        step=STS_MIN_DWELL_STEP,
        format="%.1f",
        width=PANEL_BTN_W,
        callback=lambda s, v: _on_sts_min_sit_change(v, settings),
    )
    with dpg.tooltip(parent="sts_min_sit_input"):
        dpg.add_text(
            "Seconds below the sit threshold before seated is confirmed\n"
            "and the counter is re-armed for the next rep."
        )
    dpg.add_spacer(height=4)
    dpg.add_text("", tag="sts_live_status_label")
    with dpg.tooltip(parent="sts_live_status_label"):
        dpg.add_text(
            "Live weight and posture state.\n"
            "Bar markers: centre = 50% BW; dark grey = sit–stand transition zone."
        )
    dpg.add_spacer(height=4)
    dpg.add_button(
        label="Reset STS rep counter",
        tag="reset_sts_counter_btn",
        callback=lambda: session_state.update(
            {"action": "reset_target_counter", "action_detail": "panel sts"}
        ),
        width=PANEL_BTN_W,
        height=PANEL_BTN_H,
    )
    with dpg.tooltip(parent="reset_sts_counter_btn"):
        dpg.add_text("Reset the sit-to-stand rep counter to zero.")
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
    _build_thrive_controls(settings)

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


def _on_sts_enabled_change(value: bool, settings) -> None:
    """Toggle sit-to-stand rep counter."""
    apply_setting_bool(settings, "sts_enabled", value)
    if value and not settings.sts_show_counter:
        apply_setting_bool(settings, "sts_show_counter", True)
        if dpg.does_item_exist("sts_show_counter_checkbox"):
            dpg.set_value("sts_show_counter_checkbox", True)


def _on_sts_show_counter_change(value: bool, settings) -> None:
    """Toggle on-screen STS rep counter visibility."""
    apply_setting_bool(settings, "sts_show_counter", value)


def _on_sts_stand_threshold_change(value: float, settings) -> None:
    """Update the STS stand threshold percentage."""
    clamped = apply_sts_stand_threshold_pct(settings, value)
    if dpg.does_item_exist("sts_stand_threshold_input"):
        dpg.set_value("sts_stand_threshold_input", clamped)
    if dpg.does_item_exist("sts_sit_threshold_input"):
        dpg.set_value("sts_sit_threshold_input", settings.sts_sit_threshold_pct)


def _on_sts_sit_threshold_change(value: float, settings) -> None:
    """Update the STS sit threshold percentage."""
    clamped = apply_sts_sit_threshold_pct(settings, value)
    if dpg.does_item_exist("sts_sit_threshold_input"):
        dpg.set_value("sts_sit_threshold_input", clamped)


def _on_sts_min_stand_change(value: float, settings) -> None:
    """Update the minimum stand dwell time."""
    clamped = apply_sts_min_dwell_seconds(settings, "sts_min_stand_seconds", value)
    if dpg.does_item_exist("sts_min_stand_input"):
        dpg.set_value("sts_min_stand_input", clamped)


def _on_sts_min_sit_change(value: float, settings) -> None:
    """Update the minimum sit dwell time."""
    clamped = apply_sts_min_dwell_seconds(settings, "sts_min_sit_seconds", value)
    if dpg.does_item_exist("sts_min_sit_input"):
        dpg.set_value("sts_min_sit_input", clamped)


def format_sts_live_status(app_state, settings) -> str:
    """Return the live STS status line for the settings panel.

    Args:
        app_state: Runtime session state with latest weight and STS state.
        settings: User settings including body weight and enable flag.

    Returns:
        Human-readable status string, or empty when STS is disabled.
    """
    if not settings.sts_enabled:
        return ""
    weight_kg = getattr(app_state, "sts_last_weight_kg", 0.0)
    pct = weight_pct_of_body(weight_kg, settings.body_weight_kg)
    state_label = format_sts_state_label(getattr(app_state, "sts_state", "seated"))
    return f"Live: {weight_kg:.0f} kg ({pct:.0f}% BW) - {state_label}"


def update_sts_live_status_label(app_state, settings) -> None:
    """Refresh the STS live-status label in the settings panel."""
    if not dpg.does_item_exist("sts_live_status_label"):
        return
    dpg.set_value("sts_live_status_label", format_sts_live_status(app_state, settings))


def _on_flip_vertical_toggle(settings, app_state) -> None:
    """Toggle vertical axis flip and reset sway trail/bbox extents."""
    apply_flip_vertical(settings, app_state)
    _update_flip_buttons(settings)


def _on_flip_horizontal_toggle(settings, app_state) -> None:
    """Toggle horizontal axis flip and reset sway trail/bbox extents."""
    apply_flip_horizontal(settings, app_state)
    _update_flip_buttons(settings)


def _on_zoom_change(
    value: float, settings, app_state, *, log_change: bool = True
) -> None:
    """Apply a new zoom factor and immediately rescale runtime extents."""
    apply_zoom_slider(settings, app_state, value, log_change=log_change)
