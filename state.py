# state.py
from dataclasses import dataclass, field

@dataclass
class Settings:
    """
    User-adjustable values. These start as defaults and can change
    during a session via UI controls (S2, S3, S4, S5).
    Eventually these could be persisted to a config file between sessions.
    """
    trail_length: int   = 100    # S2: number of historical positions shown
    zoom_factor: float  = 1.0    # S3: display scale multiplier
    filter_window: int  = 1      # S4: moving average window (1 = no smoothing)
    record_duration: int = 10    # S5: CSV recording duration in seconds
    cursor_mode: str    = "avatar"  # S1: "avatar" | "circle"

@dataclass
class AppState:
    """
    Mutable runtime state. Changes continuously during a session.
    Reset on RESTART.
    """
    screen_width: float  = 1280
    screen_height: float = 720
    weight: float        = 0.1   # calibrated body weight from sensitivity_calibration()
    historical_coords: list = field(default_factory=lambda: [(0, 0)] * 100)
    clicked_locations: list = field(default_factory=list)
    data_struct: dict = field(default_factory=lambda: {
        "top_right":    {"rawIndex": 3, "tare": 0},
        "bottom_right": {"rawIndex": 5, "tare": 0},
        "top_left":     {"rawIndex": 7, "tare": 0},
        "bottom_left":  {"rawIndex": 9, "tare": 0},
    })
    is_recording: bool   = False  # S5
    record_start: float  = 0.0   # S5
    record_buffer: list  = field(default_factory=list)  # S5

    def reset(self):
        """Called on RESTART — resets session data but preserves settings."""
        self.historical_coords = [(0, 0)] * 100
        self.clicked_locations = []
        self.data_struct = {
            "top_right":    {"rawIndex": 3, "tare": 0},
            "bottom_right": {"rawIndex": 5, "tare": 0},
            "top_left":     {"rawIndex": 7, "tare": 0},
            "bottom_left":  {"rawIndex": 9, "tare": 0},
        }
        self.is_recording = False
        self.record_buffer = []
