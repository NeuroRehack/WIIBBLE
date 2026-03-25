# constants.py
import os

# ---------------------------------------------------------------------------
# Hardware identifiers
# ---------------------------------------------------------------------------
VENDOR_ID  = 0x057e   # Nintendo Co., Ltd
PRODUCT_ID = 0x0306   # Wii Balance Board

# ---------------------------------------------------------------------------
# HID report byte indices for each corner sensor
# Format: data[i] = integer part of raw value, data[i+1] = fractional part (/255)
# These offsets are fixed by the WiiBalanceBoardLibrary HID report format.
# ---------------------------------------------------------------------------
SENSOR_INDICES = {
    "top_right":    3,
    "bottom_right": 5,
    "top_left":     7,
    "bottom_left":  9,
}

# ---------------------------------------------------------------------------
# Empirically derived calibration factor converting raw HID bytes to kg.
# Derivation: measured known weights against raw output, least-squares fit.
# raw_kg = (data[i] + data[i+1] / 255) * SCALE_FACTOR
# ---------------------------------------------------------------------------
SCALE_FACTOR = 2.6441910428028423

# ---------------------------------------------------------------------------
# wait_for_tare() threshold: anything below this is considered "board empty".
# The board's maximum rated capacity is ~150 kg; 530 is the raw equivalent
# of an overloaded board and is used as a practical upper bound check.
# ---------------------------------------------------------------------------
TARE_MAX_WEIGHT = 530

# ---------------------------------------------------------------------------
# sensitivity_calibration() threshold: minimum weight above the empty baseline
# to consider a person standing on the board.
# Set to 5 kg so light-contact scenarios (e.g. hands) are detected correctly.
# A value of 20 kg was too high for anything other than full body weight.
# ---------------------------------------------------------------------------
CALIB_MIN_WEIGHT_DELTA = 5

# ---------------------------------------------------------------------------
# Zoom slider range
# ---------------------------------------------------------------------------
ZOOM_SCALE = 1.01  # base of exponential zoom scaling (1.01^x)
ZOOM_MIN = -200     # minimum zoom factor (most zoomed out)
ZOOM_MAX = 600  # maximum zoom factor (most zoomed in)

# ---------------------------------------------------------------------------
# Sensitivity slider range
# ---------------------------------------------------------------------------
SENSITIVITY_MIN = 0.1   # minimum sensitivity (reduces cursor movement)
SENSITIVITY_MAX = 3.0   # maximum sensitivity (amplifies cursor movement)

# ---------------------------------------------------------------------------
# Pan (Ctrl+Scroll) settings
# ---------------------------------------------------------------------------
PAN_SPEED = 250          # pixels per mouse-wheel tick when panning
ZOOM_SPEED = 10

# ---------------------------------------------------------------------------
# Moving average filter range
# ---------------------------------------------------------------------------
FILTER_MIN = 1     # no smoothing (pass-through)
FILTER_MAX = 100    # maximum smoothing window in frames (~500ms at 60fps)

# ---------------------------------------------------------------------------
# Coordinate scaling factor — fraction of screen used for the movement range.
# Must match the value in calculate_coordinates() in data_processing.py.
# Centralised here so both the coordinate calc and zoom-to-bbox use the same value.
# ---------------------------------------------------------------------------
COORD_SCALE = 0.9

# ---------------------------------------------------------------------------
# C# board library DLL — built by: cd WiiBalanceBoardLibrary && dotnet build
# ---------------------------------------------------------------------------
DLL_RELATIVE_PATH = os.path.join(
    "WiiBalanceBoardLibrary", "bin", "Debug", "net48", "WiiBalanceBoardLibrary.dll"
)