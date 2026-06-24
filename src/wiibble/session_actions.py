"""Session and settings mutations triggered from the UI layer."""

from __future__ import annotations

from wiibble.utils.constants import (
    BOARD_CAL_REFERENCE_MAX,
    BOARD_CAL_REFERENCE_MIN,
    BODY_WEIGHT_MAX,
    BODY_WEIGHT_MIN,
    TARGET_DWELL_MAX,
    TARGET_DWELL_MIN,
    TARGET_DWELL_STEP,
    ZOOM_SCALE,
)
from wiibble.utils.recording_names import normalize_recording_prefix
from wiibble.utils.state import AppState, Settings

__all__ = [
    "apply_body_weight",
    "apply_board_cal_reference",
    "apply_cursor_size",
    "apply_filter_window",
    "apply_flip_horizontal",
    "apply_flip_vertical",
    "apply_record_duration",
    "apply_recording_dir",
    "apply_recording_prefix",
    "apply_setting_bool",
    "apply_target_dwell_seconds",
    "apply_trail_length",
    "apply_zoom_slider",
    "request_calibrate_board",
    "request_calibrate_scale",
    "start_recording_countdown",
    "stop_recording",
    "toggle_cursor_mode",
    "toggle_recording",
]


def stop_recording(app_state: AppState) -> None:
    """Stop an active or pending recording session."""
    app_state.is_recording = False
    app_state.is_countdown = False
    app_state.recording_indicator = False
    app_state.stopwatch_elapsed = 0.0


def start_recording_countdown(app_state: AppState, settings: Settings) -> None:
    """Begin the pre-recording countdown and prepare the capture buffer."""
    app_state.is_countdown = True
    app_state.countdown_value = 4
    app_state.record_duration = settings.record_duration
    app_state.record_buffer = []
    app_state.recording_indicator = False
    app_state.stopwatch_elapsed = 0.0


def toggle_recording(app_state: AppState, settings: Settings) -> bool:
    """Toggle recording on or off.

    Returns:
        True when recording or countdown is now active.
    """
    if app_state.is_recording or app_state.is_countdown:
        stop_recording(app_state)
        return False
    start_recording_countdown(app_state, settings)
    return True


def toggle_cursor_mode(settings: Settings) -> None:
    """Switch between avatar and circle cursor modes."""
    settings.toggle_cursor_mode()


def apply_cursor_size(settings: Settings, value: int) -> None:
    """Persist a new cursor size."""
    settings.cursor_size = value
    settings.save()


def apply_record_duration(settings: Settings, app_state: AppState, value: int) -> int:
    """Persist recording duration to settings and runtime state."""
    settings.record_duration = value
    app_state.record_duration = value
    settings.save()
    return value


def apply_body_weight(
    settings: Settings, app_state: AppState, value: float
) -> float | None:
    """Persist manual body weight when *value* is positive."""
    if value <= 0:
        return None
    clamped = max(BODY_WEIGHT_MIN, min(BODY_WEIGHT_MAX, float(value)))
    settings.body_weight_kg = clamped
    app_state.weight = clamped
    settings.save()
    return clamped


def apply_board_cal_reference(settings: Settings, value: float) -> float | None:
    """Persist board calibration reference mass when in range."""
    if value < BOARD_CAL_REFERENCE_MIN:
        return None
    clamped = max(BOARD_CAL_REFERENCE_MIN, min(BOARD_CAL_REFERENCE_MAX, float(value)))
    settings.board_cal_reference_kg = clamped
    settings.save()
    return clamped


def apply_recording_prefix(settings: Settings, value: str) -> str:
    """Persist a normalized recording filename prefix."""
    normalized = normalize_recording_prefix(value or "")
    settings.recording_prefix = normalized
    settings.save()
    return normalized


def apply_recording_dir(settings: Settings, path: str) -> str:
    """Persist the recording output directory."""
    settings.recording_dir = path
    settings.save()
    return path


def apply_trail_length(settings: Settings, value: int) -> int:
    """Update sway trail length."""
    settings.trail_length = value
    settings.save()
    return value


def apply_filter_window(settings: Settings, app_state: AppState, value: int) -> None:
    """Update smoothing filter window and trim the runtime buffer."""
    settings.filter_window = value
    if len(app_state.filter_buffer) > value:
        app_state.filter_buffer = app_state.filter_buffer[-value:]
    settings.save()


def apply_setting_bool(settings: Settings, field: str, value: bool) -> None:
    """Persist a boolean settings field by name."""
    setattr(settings, field, value)
    settings.save()


def apply_target_dwell_seconds(settings: Settings, value: float) -> float:
    """Clamp and persist target dwell time."""
    stepped = round(float(value) / TARGET_DWELL_STEP) * TARGET_DWELL_STEP
    clamped = max(TARGET_DWELL_MIN, min(TARGET_DWELL_MAX, stepped))
    settings.target_dwell_seconds = clamped
    settings.save()
    return clamped


def apply_flip_vertical(settings: Settings, app_state: AppState) -> bool:
    """Toggle vertical axis flip and reset sway extents."""
    settings.flip_vertical = not settings.flip_vertical
    settings.save()
    app_state.reset_sway_extents(settings.trail_length)
    return settings.flip_vertical


def apply_flip_horizontal(settings: Settings, app_state: AppState) -> bool:
    """Toggle horizontal axis flip and reset sway extents."""
    settings.flip_horizontal = not settings.flip_horizontal
    settings.save()
    app_state.reset_sway_extents(settings.trail_length)
    return settings.flip_horizontal


def apply_zoom_slider(
    settings: Settings, app_state: AppState, slider_value: float
) -> float:
    """Apply zoom from the panel slider value."""
    zoom = ZOOM_SCALE**slider_value
    settings.zoom_factor = zoom
    app_state.zoomed_max_x = app_state.raw_max_x * zoom
    app_state.zoomed_max_y = app_state.raw_max_y * zoom
    app_state.zoomed_min_x = app_state.raw_min_x * zoom
    app_state.zoomed_min_y = app_state.raw_min_y * zoom
    settings.save()
    return zoom


def request_calibrate_board(session_state: dict) -> None:
    """Queue on-board body-weight calibration in the main loop."""
    session_state["action"] = "calibrate"


def request_calibrate_scale(session_state: dict) -> None:
    """Queue board scale-factor calibration in the main loop."""
    session_state["action"] = "calibrate_scale"
