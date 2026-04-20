# state.py
import json
import logging
import os
from dataclasses import asdict, dataclass, field

log = logging.getLogger(__name__)


# Settings are persisted to this file between sessions.
SETTINGS_PATH = os.path.join(".wiibble", "settings.json")


@dataclass
class Settings:
    """
    User-adjustable values. Start as defaults, can change during a session.
    Persisted to ~/.wiibble/settings.json between sessions.
    """

    trail_length: int = 100  # S2: number of historical positions shown
    zoom_factor: float = 1.0  # S3: display scale multiplier
    filter_window: int = 1  # S4: moving average window (1 = no smoothing)
    record_duration: int = 10  # S5: CSV recording duration in seconds
    cursor_mode: str = "avatar"  # S1: "avatar" | "circle"

    def toggle_cursor_mode(self):
        """S1: Switch between avatar and circle cursor."""
        self.cursor_mode = "circle" if self.cursor_mode == "avatar" else "avatar"
        self.save()

    def save(self) -> None:
        """Persist current settings to disk."""
        try:
            os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
            with open(SETTINGS_PATH, "w") as f:
                json.dump(asdict(self), f, indent=2)
            log.info("Settings saved to %s", SETTINGS_PATH)
        except Exception:
            log.exception("Failed to save settings")

    @classmethod
    def load(cls) -> "Settings":
        """
        Load settings from disk, falling back to defaults for any
        missing or invalid fields. Safe to call even on first run.
        """
        defaults = cls()
        if not os.path.exists(SETTINGS_PATH):
            log.info("No saved settings found, using defaults.")
            return defaults
        try:
            with open(SETTINGS_PATH) as f:
                data = json.load(f)

            # Only apply keys that are valid Settings fields.
            # Unknown keys (e.g. from an older version) are silently ignored.
            valid_fields = {f.name for f in defaults.__dataclass_fields__.values()}
            filtered = {k: v for k, v in data.items() if k in valid_fields}

            loaded = cls(**filtered)
            log.info("Settings loaded from %s", SETTINGS_PATH)
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

    # Current cursor position in screen pixels — updated every frame.
    # Stored here so click handlers can access it without frame-ordering issues.
    ball_x: int = 0
    ball_y: int = 0

    historical_coords: list = field(default_factory=lambda: [(0, 0)] * 100)
    # Each target: {"center": (x, y), "radius": r} (all in logical/content coords)
    clicked_locations: list = field(default_factory=list)
    # Temporary state for a target being created (None or dict with 'center' and 'radius')
    target_in_progress: dict = None
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
