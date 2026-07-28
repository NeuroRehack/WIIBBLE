# state.py

import json
import logging
import platform
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from wiibble.utils.constants import (
    SCALE_FACTOR_DEFAULT,
    STS_MIN_DWELL_MAX,
    STS_MIN_DWELL_MIN,
    STS_MIN_DWELL_STEP,
    STS_MIN_SIT_SECONDS_DEFAULT,
    STS_MIN_STAND_SECONDS_DEFAULT,
    STS_SIT_THRESHOLD_PCT_DEFAULT,
    STS_SIT_THRESHOLD_PCT_MAX,
    STS_SIT_THRESHOLD_PCT_MIN,
    STS_STAND_THRESHOLD_PCT_DEFAULT,
    STS_STAND_THRESHOLD_PCT_MAX,
    STS_STAND_THRESHOLD_PCT_MIN,
    TARGET_DWELL_DEFAULT,
    TARGET_DWELL_MAX,
    TARGET_DWELL_MIN,
    TARGET_DWELL_STEP,
)
from wiibble.utils.recording_names import normalize_recording_prefix

log = logging.getLogger(__name__)

_TARE_CORNER_FIELDS = (
    ("top_right", "tare_top_right"),
    ("bottom_right", "tare_bottom_right"),
    ("top_left", "tare_top_left"),
    ("bottom_left", "tare_bottom_left"),
)


def default_data_struct() -> dict:
    """Return a fresh per-corner HID mapping with zero tare offsets."""
    return {
        "top_right": {"rawIndex": 3, "tare": 0},
        "bottom_right": {"rawIndex": 5, "tare": 0},
        "top_left": {"rawIndex": 7, "tare": 0},
        "bottom_left": {"rawIndex": 9, "tare": 0},
    }


def get_settings_path() -> Path:
    """Return the platform-specific settings file path."""
    import os

    override = os.environ.get("WIIBBLE_SETTINGS_PATH")
    if override:
        return Path(override)
    if platform.system() == "Windows":
        appdata = Path(os.environ.get("APPDATA", Path.home()))
        return appdata / "WIIBBLE" / "settings.json"
    return Path.home() / ".wiibble" / "settings.json"


@dataclass
class Settings:
    """
    User-adjustable values. Start as defaults, can change during a session.
    Persisted to the platform settings file between sessions (see
    :func:`get_settings_path`; on Windows ``%APPDATA%\\WIIBBLE\\settings.json``).
    """

    trail_length: int = 100  # S2: number of historical positions shown
    zoom_factor: float = 1.0  # S3: display scale multiplier
    filter_window: int = 1  # S4: moving average window (1 = no smoothing)
    record_duration: int = 30  # S5: CSV recording duration in seconds (0 = indefinite)
    cursor_mode: str = "circle"  # S1: "avatar" | "circle"
    cursor_size: int = 20  # S1: circle radius / avatar half-height in pixels
    show_bbox: bool = True  # whether to show the bounding box on canvas
    show_global_axes: bool = True  # solid crosshairs at screen centre
    show_local_axes: bool = False  # dotted crosshairs at sway-bbox centre
    target_dwell_seconds: float = (
        TARGET_DWELL_DEFAULT  # hold time to increment hit counter
    )
    show_target_counter: bool = True  # whether to show the on-screen hit counter
    flip_horizontal: bool = False  # invert left-right display and recording mapping
    flip_vertical: bool = False  # invert forward-back display and recording mapping
    recording_dir: str = ""  # output folder for CSV recordings ("" = use default)
    recording_prefix: str = ""  # filename prefix ("" = use default "recording")
    body_weight_kg: float = (
        70.0  # reference body weight for cursor normalization and recordings
    )
    scale_factor: float = SCALE_FACTOR_DEFAULT  # HID raw → kg conversion for this board
    board_cal_reference_kg: float = 20.0  # known mass used for board scale calibration
    auto_report_after_recording: bool = True  # HTML report when recording ends
    open_report_in_browser: bool = True  # open report in browser after generation
    thrive_enabled: bool = False  # publish live data to THRIVE hub via MQTT
    thrive_broker_host: str = "localhost"  # THRIVE PC LAN IP (Mosquitto)
    thrive_hub_id: str = "demo"  # must match THRIVE .env HUB_ID
    thrive_node_id: str = "wiibble_01"  # MQTT node id (distinct from simulator)
    tare_top_right: float = 0.0
    tare_bottom_right: float = 0.0
    tare_top_left: float = 0.0
    tare_bottom_left: float = 0.0
    tare_saved_at: str = ""  # ISO-8601 UTC; empty means never tared
    sts_enabled: bool = False  # enable sit-to-stand rep counter
    sts_show_counter: bool = True  # show on-screen STS rep counter
    sts_stand_threshold_pct: float = STS_STAND_THRESHOLD_PCT_DEFAULT
    sts_sit_threshold_pct: float = STS_SIT_THRESHOLD_PCT_DEFAULT
    sts_min_stand_seconds: float = STS_MIN_STAND_SECONDS_DEFAULT
    sts_min_sit_seconds: float = STS_MIN_SIT_SECONDS_DEFAULT

    def has_saved_tare(self) -> bool:
        """Return True when persisted tare offsets are available."""
        return bool(self.tare_saved_at)

    def apply_tare_to_data_struct(self, data_struct: dict) -> None:
        """Copy persisted tare offsets into runtime ``data_struct`` corner entries."""
        for corner_key, field_name in _TARE_CORNER_FIELDS:
            data_struct[corner_key]["tare"] = getattr(self, field_name)

    def save_tare_from_data_struct(self, data_struct: dict) -> None:
        """Persist corner tare offsets from ``data_struct`` and write settings to disk.

        UI label refresh is handled by
        :func:`wiibble.ui.calibration_flow.run_tare_and_persist`.
        """
        for corner_key, field_name in _TARE_CORNER_FIELDS:
            setattr(self, field_name, float(data_struct[corner_key]["tare"]))
        self.tare_saved_at = datetime.now(UTC).isoformat()
        self.save()

    def toggle_cursor_mode(self) -> None:
        """Switch between avatar and circle cursor display modes."""
        self.cursor_mode = "circle" if self.cursor_mode == "avatar" else "avatar"
        self.save()

    def save(self) -> None:
        """Persist current settings to disk."""
        path = get_settings_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
            log.debug("Settings saved to %s", path)
        except Exception:
            log.exception("Failed to save settings")

    @classmethod
    def load(cls) -> "Settings":
        """
        Load settings from disk, falling back to defaults for any
        missing or invalid fields. Safe to call even on first run.
        """
        path = get_settings_path()
        defaults = cls()
        if not path.is_file():
            log.info("No saved settings found, using defaults.")
            return defaults
        try:
            data = json.loads(path.read_text(encoding="utf-8"))

            # Only apply keys that are valid Settings fields.
            # Unknown keys (e.g. from an older version) are silently ignored.
            valid_fields = {f.name for f in defaults.__dataclass_fields__.values()}
            merged = defaults.__dict__.copy()
            merged.update({k: v for k, v in data.items() if k in valid_fields})
            loaded = cls(**merged)
            stepped = round(float(loaded.target_dwell_seconds) / TARGET_DWELL_STEP)
            loaded.target_dwell_seconds = max(
                TARGET_DWELL_MIN,
                min(TARGET_DWELL_MAX, stepped * TARGET_DWELL_STEP),
            )
            loaded.sts_stand_threshold_pct = max(
                STS_STAND_THRESHOLD_PCT_MIN,
                min(STS_STAND_THRESHOLD_PCT_MAX, float(loaded.sts_stand_threshold_pct)),
            )
            loaded.sts_sit_threshold_pct = max(
                STS_SIT_THRESHOLD_PCT_MIN,
                min(STS_SIT_THRESHOLD_PCT_MAX, float(loaded.sts_sit_threshold_pct)),
            )
            if loaded.sts_sit_threshold_pct >= loaded.sts_stand_threshold_pct:
                loaded.sts_sit_threshold_pct = max(
                    STS_SIT_THRESHOLD_PCT_MIN,
                    loaded.sts_stand_threshold_pct - 10.0,
                )
            for field_name in ("sts_min_stand_seconds", "sts_min_sit_seconds"):
                stepped_sts = round(
                    float(getattr(loaded, field_name)) / STS_MIN_DWELL_STEP
                )
                setattr(
                    loaded,
                    field_name,
                    max(
                        STS_MIN_DWELL_MIN,
                        min(STS_MIN_DWELL_MAX, stepped_sts * STS_MIN_DWELL_STEP),
                    ),
                )
            raw_prefix = loaded.recording_prefix
            loaded.recording_prefix = normalize_recording_prefix(raw_prefix)
            if loaded.recording_prefix != raw_prefix:
                loaded.save()
            if loaded.cursor_mode not in ("avatar", "circle"):
                loaded.cursor_mode = "circle"
            log.info("Settings loaded from %s", path)
            return loaded
        except Exception as e:
            log.warning("Failed to load settings (%s), using defaults.", e)
            return defaults


@dataclass
class AppState:
    """
    Mutable runtime state. Changes continuously during a session.
    Reset on RESTART. Screen dimensions and weight are NOT reset
    (they reflect hardware/calibration, not session data).
    """

    screen_width: float = 1280
    screen_height: float = 720
    weight: float = 0.1  # calibrated body weight from sensitivity_calibration()
    scale_factor: float = (
        SCALE_FACTOR_DEFAULT  # runtime HID → kg factor (synced from settings)
    )

    # Current cursor position in screen pixels — updated every frame.
    # Stored here so click handlers can access it without frame-ordering issues.
    ball_x: int = 0
    ball_y: int = 0

    historical_coords: list = field(default_factory=lambda: [(0, 0)] * 100)
    # Each target: circle {"center", "radius"} or rect {"shape":"rect", "min", "max"}
    clicked_locations: list = field(default_factory=list)
    # Temporary state for a target being created (None or in-progress target dict)
    target_in_progress: dict = None
    # Target reposition drag — {"index": int, "grab_offset": (dx, dy)} in logical coords
    target_move_in_progress: dict = None
    # Target resize drag — {"index": int, "shape": str, "edge": str|None}
    target_resize_in_progress: dict = None
    # Cursor drag-to-resize state
    cursor_drag_in_progress: bool = False
    cursor_drag_start_size: int = 20
    data_struct: dict = field(default_factory=default_data_struct)
    is_recording: bool = False  # S5
    record_start: float = 0.0  # S5
    record_buffer: list = field(default_factory=list)  # S5
    # Stopwatch timer for recording
    stopwatch_elapsed: float = 0.0  # Elapsed time in seconds (for UI)

    # S5: Timed Data Recording to CSV — countdown and status
    is_countdown: bool = False  # True if countdown is active
    countdown_value: int = 0  # 3, 2, 1, 0 (seconds left)
    record_duration: float = 30.0  # Duration in seconds (copied from settings at start)
    recording_indicator: bool = False  # For UI (e.g. red dot/REC)

    # Moving average filter buffer — stores last N raw corner kg dicts.
    # Averaging happens before calculate_coordinates() so noise is suppressed
    # at the sensor level, not in scaled coordinate space.
    # filter_window=1 means no smoothing (pass-through).
    filter_buffer: list = field(default_factory=list)

    # Latest unfiltered (raw) corner kg values from parse_data().
    # Recording always uses these so CSV data is never pre-smoothed by the UI
    # filter, regardless of the current filter_window setting.
    raw_corners: dict = field(
        default_factory=lambda: {
            "top_right": 0.0,
            "bottom_right": 0.0,
            "top_left": 0.0,
            "bottom_left": 0.0,
        }
    )

    # Pan offset — Ctrl+Scroll shifts the canvas centre so users can focus on
    # off-centre regions. Stored in pixels (viewport coords).
    pan_offset_x: float = 0.0
    pan_offset_y: float = 0.0

    # Raw (zoom=1.0) coordinate extents — used for zoom-to-bbox and
    # live bounding box rescaling when zoom slider changes.
    raw_max_x: float = 0.0
    raw_max_y: float = 0.0
    raw_min_x: float = 0.0
    raw_min_y: float = 0.0

    # Zoomed extents (raw * zoom_factor) — what the bounding box actually draws.
    # Kept in app_state so _on_zoom_change() can update them without local vars.
    zoomed_max_x: float = 0.0
    zoomed_max_y: float = 0.0
    zoomed_min_x: float = 0.0
    zoomed_min_y: float = 0.0

    # Toast overlay — brief canvas banner shown after a recording is saved.
    toast_message: str = ""
    toast_until: float = 0.0

    # End-of-session report — path to last HTML report; async companion job while set.
    last_report_path: str = ""
    last_recording_csv_path: str = ""
    report_job: dict | None = None
    report_progress: dict | None = None

    # Target dwell hit counter — session runtime only
    target_hit_count: int = 0
    _target_dwell_elapsed: dict = field(
        default_factory=dict
    )  # per-target seconds while armed
    _target_dwell_disarmed: set = field(
        default_factory=set
    )  # targets awaiting exit before re-count
    _target_dwell_last_tick: float = 0.0

    # Sit-to-stand rep counter — session runtime only
    sts_rep_count: int = 0
    sts_state: str = "seated"
    sts_stand_dwell: float = 0.0
    sts_sit_dwell: float = 0.0
    sts_last_tick: float = 0.0
    sts_last_weight_kg: float = 0.0
    sts_rep_flash_until: float = 0.0
    sts_disarmed: bool = False  # after a rep, must sit before next count

    def reset_sway_extents(self, trail_length: int) -> None:
        """Clear sway trail and bounding-box extents (e.g. after axis flip)."""
        self.historical_coords = [(0, 0)] * trail_length
        self.raw_max_x = self.raw_max_y = 0.0
        self.raw_min_x = self.raw_min_y = 0.0
        self.zoomed_max_x = self.zoomed_max_y = 0.0
        self.zoomed_min_x = self.zoomed_min_y = 0.0

    def reset_target_counter(self) -> None:
        """Reset the target dwell hit counter and dwell timer state."""
        self.target_hit_count = 0
        self._target_dwell_elapsed = {}
        self._target_dwell_disarmed = set()
        self._target_dwell_last_tick = 0.0

    def reset_sts_counter(self) -> None:
        """Reset the sit-to-stand rep counter and internal state machine."""
        self.sts_rep_count = 0
        self.sts_state = "seated"
        self.sts_stand_dwell = 0.0
        self.sts_sit_dwell = 0.0
        self.sts_last_tick = 0.0
        self.sts_rep_flash_until = 0.0
        self.sts_disarmed = False

    def reset(self, settings: Settings | None = None) -> None:
        """Called on RESTART — resets session data but preserves calibration."""
        self.ball_x = 0
        self.ball_y = 0
        self.historical_coords = [(0, 0)] * 100
        self.clicked_locations = []
        self.data_struct = default_data_struct()
        if settings is not None and settings.has_saved_tare():
            settings.apply_tare_to_data_struct(self.data_struct)
        self.reset_target_counter()
        self.reset_sts_counter()
        self.is_recording = False
        self.record_buffer = []
        self.filter_buffer = []
        self.raw_max_x = self.raw_max_y = 0.0
        self.raw_min_x = self.raw_min_y = 0.0
        self.zoomed_max_x = self.zoomed_max_y = 0.0
        self.zoomed_min_x = self.zoomed_min_y = 0.0
        self.pan_offset_x = 0.0
        self.pan_offset_y = 0.0
        self.is_countdown = False
        self.countdown_value = 0
        self.record_duration = 30.0
        self.recording_indicator = False
        self.last_report_path = ""
        self.last_recording_csv_path = ""
        self.report_job = None
        self.report_progress = None
        self.cursor_drag_in_progress = False
        self.cursor_drag_start_size = 20
        self.target_in_progress = None
        self.target_move_in_progress = None
        self.target_resize_in_progress = None
        self.toast_message = ""
        self.toast_until = 0.0
