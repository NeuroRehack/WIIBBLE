# state.py

import json
import logging
import os
import platform
from dataclasses import asdict, dataclass, field

from wiibble.board.recording import normalize_recording_prefix
from wiibble.utils.constants import SCALE_FACTOR_DEFAULT, TARGET_DWELL_DEFAULT, TARGET_DWELL_MAX, TARGET_DWELL_MIN

log = logging.getLogger(__name__)


def get_settings_path():
    override = os.environ.get("WIIBBLE_SETTINGS_PATH")
    if override:
        return override
    if platform.system() == "Windows":
        return os.path.join(
            os.environ.get("APPDATA", os.path.expanduser("~")), "WIIBBLE", "settings.json"
        )
    return os.path.join(os.path.expanduser("~/.wiibble"), "settings.json")


@dataclass
class Settings:
    """
    User-adjustable values. Start as defaults, can change during a session.
    Persisted to ~/.wiibble/settings.json between sessions.
    """

    trail_length: int = 100  # S2: number of historical positions shown
    zoom_factor: float = 1.0  # S3: display scale multiplier
    filter_window: int = 1  # S4: moving average window (1 = no smoothing)
    record_duration: int = 10  # S5: CSV recording duration in seconds (0 = indefinite)
    cursor_mode: str = "avatar"  # S1: "avatar" | "circle"
    cursor_size: int = 20  # S1: circle cursor radius in pixels
    show_bbox: bool = True  # whether to show the bounding box on canvas
    show_global_axes: bool = True  # solid crosshairs at screen centre
    show_local_axes: bool = False  # dotted crosshairs at sway-bbox centre
    target_jelly: bool = True  # whether targets animate with jelly effect on hit
    target_dwell_seconds: int = TARGET_DWELL_DEFAULT  # hold time to increment hit counter
    show_target_counter: bool = True  # whether to show the on-screen hit counter
    flip_horizontal: bool = False  # invert left-right display and recording mapping
    flip_vertical: bool = False  # invert forward-back display and recording mapping
    recording_dir: str = ""  # output folder for CSV recordings ("" = use default)
    recording_prefix: str = ""  # filename prefix ("" = use default "recording")
    body_weight_kg: float = 70.0  # reference body weight for cursor normalization and recordings
    scale_factor: float = SCALE_FACTOR_DEFAULT  # HID raw → kg conversion for this board
    board_cal_reference_kg: float = 20.0  # known mass used for board scale calibration

    def toggle_cursor_mode(self):
        """S1: Switch between avatar and circle cursor."""
        self.cursor_mode = "circle" if self.cursor_mode == "avatar" else "avatar"
        self.save()

    def save(self) -> None:
        """Persist current settings to disk."""
        path = get_settings_path()
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                json.dump(asdict(self), f, indent=2)
            log.info("Settings saved to %s", path)
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
        if not os.path.exists(path):
            log.info("No saved settings found, using defaults.")
            return defaults
        try:
            with open(path) as f:
                data = json.load(f)

            # Only apply keys that are valid Settings fields.
            # Unknown keys (e.g. from an older version) are silently ignored.
            valid_fields = {f.name for f in defaults.__dataclass_fields__.values()}
            merged = defaults.__dict__.copy()
            merged.update({k: v for k, v in data.items() if k in valid_fields})
            loaded = cls(**merged)
            if isinstance(loaded.target_dwell_seconds, float):
                loaded.target_dwell_seconds = int(round(loaded.target_dwell_seconds))
            loaded.target_dwell_seconds = max(
                TARGET_DWELL_MIN, min(TARGET_DWELL_MAX, int(loaded.target_dwell_seconds))
            )
            raw_prefix = loaded.recording_prefix
            loaded.recording_prefix = normalize_recording_prefix(raw_prefix)
            if loaded.recording_prefix != raw_prefix:
                loaded.save()
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
    scale_factor: float = SCALE_FACTOR_DEFAULT  # runtime HID → kg factor (synced from settings)

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
    # Cursor drag-to-resize state
    cursor_drag_in_progress: bool = False
    cursor_drag_start_size: int = 20
    data_struct: dict = field(
        default_factory=lambda: {
            "top_right": {"rawIndex": 3, "tare": 0},
            "bottom_right": {"rawIndex": 5, "tare": 0},
            "top_left": {"rawIndex": 7, "tare": 0},
            "bottom_left": {"rawIndex": 9, "tare": 0},
        }
    )
    is_recording: bool = False  # S5
    record_start: float = 0.0  # S5
    record_buffer: list = field(default_factory=list)  # S5
    # Stopwatch timer for recording
    stopwatch_elapsed: float = 0.0  # Elapsed time in seconds (for UI)

    # S5: Timed Data Recording to CSV — countdown and status
    is_countdown: bool = False  # True if countdown is active
    countdown_value: int = 0  # 3, 2, 1, 0 (seconds left)
    record_duration: float = 10.0  # Duration in seconds (copied from settings at start)
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

    # Ripple animations — per-target jelly oscillation ages, keyed by target index.
    # Value is the frame age since the hit; absent/removed when animation ends.
    _jelly_ages: dict = field(default_factory=dict)
    # Previous per-target hit states for edge detection — keyed by target index
    _prev_hit_states: dict = field(default_factory=dict)

    # Target dwell hit counter — session runtime only
    target_hit_count: int = 0
    _target_dwell_elapsed: dict = field(default_factory=dict)  # per-target seconds while armed
    _target_dwell_disarmed: set = field(default_factory=set)  # targets awaiting exit before re-count
    _target_dwell_last_tick: float = 0.0

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

    def reset(self):
        """Called on RESTART — resets session data but preserves calibration."""
        self.ball_x = 0
        self.ball_y = 0
        self.historical_coords = [(0, 0)] * 100
        self.clicked_locations = []
        self.data_struct = {
            "top_right": {"rawIndex": 3, "tare": 0},
            "bottom_right": {"rawIndex": 5, "tare": 0},
            "top_left": {"rawIndex": 7, "tare": 0},
            "bottom_left": {"rawIndex": 9, "tare": 0},
        }
        self.reset_target_counter()
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
        self.record_duration = 10.0
        self.recording_indicator = False
        self.cursor_drag_in_progress = False
        self.cursor_drag_start_size = 20
        self.target_in_progress = None
        self.target_move_in_progress = None
        self.toast_message = ""
        self.toast_until = 0.0
        self._jelly_ages = {}
        self._prev_hit_states = {}
