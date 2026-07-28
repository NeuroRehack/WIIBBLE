"""Session and settings mutations triggered from the UI layer."""

from __future__ import annotations

import logging

from wiibble.utils.constants import (
    BOARD_CAL_REFERENCE_MAX,
    BOARD_CAL_REFERENCE_MIN,
    BODY_WEIGHT_MAX,
    BODY_WEIGHT_MIN,
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
    ZOOM_SCALE,
)
from wiibble.utils.recording_names import normalize_recording_prefix
from wiibble.utils.state import AppState, Settings

log = logging.getLogger(__name__)

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
    "apply_sts_min_dwell_seconds",
    "apply_sts_sit_threshold_pct",
    "apply_sts_stand_threshold_pct",
    "apply_trail_length",
    "apply_zoom_slider",
    "request_calibrate_board",
    "request_calibrate_scale",
    "start_recording_countdown",
    "stop_recording",
    "toggle_recording",
]

_SETTING_LABELS: dict[str, str] = {
    "show_bbox": "Show bounding box",
    "show_global_axes": "Show global axes",
    "show_local_axes": "Show local axes",
    "show_target_counter": "Show target hit counter",
    "sts_enabled": "Sit-to-stand rep counter",
    "sts_show_counter": "Show STS rep counter",
    "auto_report_after_recording": "Auto-report after recording",
    "open_report_in_browser": "Open report in browser",
    "thrive_enabled": "THRIVE hub export",
}


def stop_recording(app_state: AppState, *, source: str = "control") -> None:
    """Stop an active or pending recording session."""
    if app_state.is_recording or app_state.is_countdown:
        log.info("Recording stopped (%s)", source)
    app_state.is_recording = False
    app_state.is_countdown = False
    app_state.recording_indicator = False
    app_state.stopwatch_elapsed = 0.0


def start_recording_countdown(app_state: AppState, settings: Settings) -> None:
    """Begin the pre-recording countdown and prepare the capture buffer."""
    duration = settings.record_duration
    label = "indefinite" if duration <= 0 else f"{duration}s"
    log.info("Recording countdown started (duration=%s)", label)
    app_state.is_countdown = True
    app_state.countdown_value = 4
    app_state.record_duration = duration
    app_state.record_buffer = []
    app_state.recording_indicator = False
    app_state.stopwatch_elapsed = 0.0


def toggle_recording(
    app_state: AppState, settings: Settings, *, source: str = "control"
) -> bool:
    """Toggle recording on or off.

    Returns:
        True when recording or countdown is now active.
    """
    if app_state.is_recording or app_state.is_countdown:
        stop_recording(app_state, source=source)
        return False
    start_recording_countdown(app_state, settings)
    return True


def apply_cursor_size(
    settings: Settings, value: int, *, log_change: bool = True
) -> None:
    """Persist a new cursor size."""
    if settings.cursor_size == value:
        return
    settings.cursor_size = value
    if log_change:
        log.info("Cursor size set to %d px", value)
    settings.save()


def apply_record_duration(settings: Settings, app_state: AppState, value: int) -> int:
    """Persist recording duration to settings and runtime state."""
    if settings.record_duration == value:
        return value
    settings.record_duration = value
    app_state.record_duration = value
    label = "indefinite" if value <= 0 else f"{value}s"
    log.info("Recording duration set to %s", label)
    settings.save()
    return value


def apply_body_weight(
    settings: Settings, app_state: AppState, value: float
) -> float | None:
    """Persist manual body weight when *value* is positive."""
    if value <= 0:
        return None
    clamped = max(BODY_WEIGHT_MIN, min(BODY_WEIGHT_MAX, float(value)))
    if settings.body_weight_kg == clamped:
        return clamped
    settings.body_weight_kg = clamped
    app_state.weight = clamped
    log.info("Body weight set to %.1f kg (manual)", clamped)
    settings.save()
    return clamped


def apply_board_cal_reference(settings: Settings, value: float) -> float | None:
    """Persist board calibration reference mass when in range."""
    if value < BOARD_CAL_REFERENCE_MIN:
        return None
    clamped = max(BOARD_CAL_REFERENCE_MIN, min(BOARD_CAL_REFERENCE_MAX, float(value)))
    if settings.board_cal_reference_kg == clamped:
        return clamped
    settings.board_cal_reference_kg = clamped
    log.info("Board reference mass set to %.1f kg", clamped)
    settings.save()
    return clamped


def apply_recording_prefix(settings: Settings, value: str) -> str:
    """Persist a normalized recording filename prefix."""
    normalized = normalize_recording_prefix(value or "")
    if settings.recording_prefix == normalized:
        return normalized
    settings.recording_prefix = normalized
    log.info("Recording prefix set to %r", normalized)
    settings.save()
    return normalized


def apply_recording_dir(settings: Settings, path: str) -> str:
    """Persist the recording output directory."""
    if settings.recording_dir == path:
        return path
    settings.recording_dir = path
    log.info("Recording output directory set to %s", path)
    settings.save()
    return path


def apply_trail_length(settings: Settings, value: int) -> int:
    """Update sway trail length."""
    if settings.trail_length == value:
        return value
    settings.trail_length = value
    log.info("Sway trail length set to %d", value)
    settings.save()
    return value


def apply_filter_window(settings: Settings, app_state: AppState, value: int) -> None:
    """Update smoothing filter window and trim the runtime buffer."""
    if settings.filter_window == value:
        return
    settings.filter_window = value
    log.info("Smoothing filter set to %d frames", value)
    if len(app_state.filter_buffer) > value:
        app_state.filter_buffer = app_state.filter_buffer[-value:]
    settings.save()


def apply_setting_bool(settings: Settings, field: str, value: bool) -> None:
    """Persist a boolean settings field by name."""
    if getattr(settings, field) == value:
        return
    setattr(settings, field, value)
    label = _SETTING_LABELS.get(field, field.replace("_", " "))
    log.info("%s: %s", label, "on" if value else "off")
    settings.save()


def apply_target_dwell_seconds(settings: Settings, value: float) -> float:
    """Clamp and persist target dwell time."""
    stepped = round(float(value) / TARGET_DWELL_STEP) * TARGET_DWELL_STEP
    clamped = max(TARGET_DWELL_MIN, min(TARGET_DWELL_MAX, stepped))
    if settings.target_dwell_seconds == clamped:
        return clamped
    settings.target_dwell_seconds = clamped
    log.info("Target dwell time set to %.1f s", clamped)
    settings.save()
    return clamped


def _clamp_sts_dwell_seconds(value: float) -> float:
    """Clamp an STS minimum dwell time to the allowed range."""
    stepped = round(float(value) / STS_MIN_DWELL_STEP) * STS_MIN_DWELL_STEP
    return max(STS_MIN_DWELL_MIN, min(STS_MIN_DWELL_MAX, stepped))


def apply_sts_stand_threshold_pct(settings: Settings, value: float) -> float:
    """Clamp and persist the STS stand threshold percentage."""
    clamped = max(
        STS_STAND_THRESHOLD_PCT_MIN,
        min(STS_STAND_THRESHOLD_PCT_MAX, float(value)),
    )
    if settings.sts_stand_threshold_pct == clamped:
        return clamped
    settings.sts_stand_threshold_pct = clamped
    if settings.sts_sit_threshold_pct >= clamped:
        settings.sts_sit_threshold_pct = max(
            STS_SIT_THRESHOLD_PCT_MIN, clamped - 10.0
        )
    log.info("STS stand threshold set to %.1f%% body weight", clamped)
    settings.save()
    return clamped


def apply_sts_sit_threshold_pct(settings: Settings, value: float) -> float:
    """Clamp and persist the STS sit threshold percentage."""
    clamped = max(
        STS_SIT_THRESHOLD_PCT_MIN,
        min(STS_SIT_THRESHOLD_PCT_MAX, float(value)),
    )
    max_sit = settings.sts_stand_threshold_pct - 1.0
    clamped = min(clamped, max(STS_SIT_THRESHOLD_PCT_MIN, max_sit))
    if settings.sts_sit_threshold_pct == clamped:
        return clamped
    settings.sts_sit_threshold_pct = clamped
    log.info("STS sit threshold set to %.1f%% body weight", clamped)
    settings.save()
    return clamped


def apply_sts_min_dwell_seconds(
    settings: Settings, field: str, value: float
) -> float:
    """Clamp and persist an STS minimum dwell time field."""
    clamped = _clamp_sts_dwell_seconds(value)
    if getattr(settings, field) == clamped:
        return clamped
    setattr(settings, field, clamped)
    label = "stand" if field == "sts_min_stand_seconds" else "sit"
    log.info("STS min %s time set to %.1f s", label, clamped)
    settings.save()
    return clamped


def apply_flip_vertical(settings: Settings, app_state: AppState) -> bool:
    """Toggle vertical axis flip and reset sway extents."""
    settings.flip_vertical = not settings.flip_vertical
    log.info("Flip vertical: %s", "on" if settings.flip_vertical else "off")
    settings.save()
    app_state.reset_sway_extents(settings.trail_length)
    return settings.flip_vertical


def apply_flip_horizontal(settings: Settings, app_state: AppState) -> bool:
    """Toggle horizontal axis flip and reset sway extents."""
    settings.flip_horizontal = not settings.flip_horizontal
    log.info("Flip horizontal: %s", "on" if settings.flip_horizontal else "off")
    settings.save()
    app_state.reset_sway_extents(settings.trail_length)
    return settings.flip_horizontal


def apply_zoom_slider(
    settings: Settings,
    app_state: AppState,
    slider_value: float,
    *,
    log_change: bool = True,
) -> float:
    """Apply zoom from the panel slider value."""
    zoom = ZOOM_SCALE**slider_value
    if settings.zoom_factor == zoom:
        return zoom
    settings.zoom_factor = zoom
    app_state.zoomed_max_x = app_state.raw_max_x * zoom
    app_state.zoomed_max_y = app_state.raw_max_y * zoom
    app_state.zoomed_min_x = app_state.raw_min_x * zoom
    app_state.zoomed_min_y = app_state.raw_min_y * zoom
    if log_change:
        log.info("Zoom factor set to %.2fx", zoom)
    settings.save()
    return zoom


def request_calibrate_board(session_state: dict) -> None:
    """Queue on-board body-weight calibration in the main loop."""
    session_state["action"] = "calibrate"


def request_calibrate_scale(session_state: dict) -> None:
    """Queue board scale-factor calibration in the main loop."""
    session_state["action"] = "calibrate_scale"


def apply_thrive_broker_host(settings: Settings, value: str) -> str:
    """Persist THRIVE MQTT broker hostname."""
    host = (value or "").strip() or "localhost"
    if settings.thrive_broker_host == host:
        return host
    settings.thrive_broker_host = host
    log.info("THRIVE broker host set to %s", host)
    settings.save()
    return host


def apply_thrive_hub_id(settings: Settings, value: str) -> str:
    """Persist THRIVE hub ID (MQTT topic segment)."""
    hub_id = (value or "").strip() or "demo"
    if settings.thrive_hub_id == hub_id:
        return hub_id
    settings.thrive_hub_id = hub_id
    log.info("THRIVE hub ID set to %s", hub_id)
    settings.save()
    return hub_id
