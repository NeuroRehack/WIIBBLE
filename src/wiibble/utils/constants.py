"""Application constants and hardware configuration for WIIBBLE.

This module centralizes all fixed values used by the app, including hardware
identifiers, sensor layout mapping, calibration thresholds, and UI layout
constants.
"""

import os

# ---------------------------------------------------------------------------
# Hardware identifiers
# ---------------------------------------------------------------------------
VENDOR_ID = 0x057E  # Nintendo Co., Ltd
PRODUCT_ID = 0x0306  # Wii Balance Board

# ---------------------------------------------------------------------------
# HID report byte indices for each corner sensor
# Format: data[i] = integer part of raw value, data[i+1] = fractional part (/255)
# These offsets are fixed by the WiiBalanceBoardLibrary HID report format.
# ---------------------------------------------------------------------------
SENSOR_INDICES = {
    "top_right": 3,
    "bottom_right": 5,
    "top_left": 7,
    "bottom_left": 9,
}

# ---------------------------------------------------------------------------
# Empirically derived calibration factor converting raw HID bytes to kg.
# Derivation: measured known weights against raw output, least-squares fit.
# raw_kg = (data[i] + data[i+1] / 255) * scale_factor
# ---------------------------------------------------------------------------
SCALE_FACTOR_DEFAULT = 2.6441910428028423
SCALE_FACTOR = SCALE_FACTOR_DEFAULT  # backward-compatible alias

# ---------------------------------------------------------------------------
# Board scale calibration (reference mass on board → scale_factor)
# ---------------------------------------------------------------------------
BOARD_CAL_REFERENCE_MIN = 10.0
BOARD_CAL_REFERENCE_MAX = 150.0
BOARD_CAL_REFERENCE_DEFAULT = 20.0
SCALE_FACTOR_MIN = 0.5
SCALE_FACTOR_MAX = 10.0
RAW_STABILITY_DELTA = 0.5  # max change in tared raw sum between consecutive samples

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
# Body weight reference (settings panel manual entry and defaults)
# ---------------------------------------------------------------------------
BODY_WEIGHT_DEFAULT = 70.0
BODY_WEIGHT_MIN = 1.0
BODY_WEIGHT_MAX = 150.0  # Wii Balance Board rated capacity

# ---------------------------------------------------------------------------
# Zoom slider range
# ---------------------------------------------------------------------------
ZOOM_SCALE = 1.01  # base of exponential zoom scaling (1.01^x)
ZOOM_MIN = -200  # minimum zoom factor (most zoomed out)
ZOOM_MAX = 600  # maximum zoom factor (most zoomed in)

# ---------------------------------------------------------------------------
# Pan (Ctrl+Scroll) settings
# ---------------------------------------------------------------------------
PAN_SPEED = 250  # pixels per mouse-wheel tick when panning
ZOOM_SPEED = 10

# ---------------------------------------------------------------------------
# Moving average filter range
# ---------------------------------------------------------------------------
FILTER_MIN = 1  # no smoothing (pass-through)
FILTER_MAX = 100  # maximum smoothing window in frames (~500ms at 60fps)

# ---------------------------------------------------------------------------
# Coordinate scaling factor — fraction of screen used for the movement range.
# Must match the value in calculate_coordinates() in data_processing.py.
# Centralised here so both the coordinate calc and zoom-to-bbox use the same value.
# ---------------------------------------------------------------------------
COORD_SCALE = 0.9

# ---------------------------------------------------------------------------
# UI layout constants — settings panel (left-side vertical drawer)
# ---------------------------------------------------------------------------
PANEL_W = 340  # settings panel width in pixels (wider)
PANEL_BTN_H = 36  # standard panel button height
PANEL_BTN_W = 290  # full-width panel button (wider)
PANEL_SLIDER_W = 290  # slider width inside panel (wider)
PANEL_COMBO_W = 290  # combo width inside panel (wider)
PANEL_TOGGLE_BTN_SIZE = 40  # floating toggle button size
PANEL_SECTION_SPACING = 6  # vertical padding between sections

# Canvas quick-access floating toolbar (clear screen, recording toggle)
QUICK_ACCESS_MARGIN = 4  # px from viewport edge
QUICK_ACCESS_GAP = 4  # px between adjacent quick-access buttons

# Top-right recording indicator cluster (timer + quick-access record button + limit)
RECORDING_INDICATOR_RIGHT_MARGIN = 20
RECORDING_INDICATOR_DOT_RADIUS = 18
RECORDING_INDICATOR_SPACING = 12
RECORDING_INDICATOR_Y = 8
RECORDING_INDICATOR_TIMER_FONT_SIZE = 48  # elapsed time while recording
RECORDING_INDICATOR_LIMIT_FONT_SIZE = 48  # configured duration limit (always visible)
# Approximate text widths — used only to anchor labels beside the record button.
RECORDING_INDICATOR_LIMIT_WIDTH = int(RECORDING_INDICATOR_LIMIT_FONT_SIZE * 0.58 * 5)
RECORDING_INDICATOR_ELAPSED_CHAR_WIDTH = 0.58  # em width per character (digits / punctuation)

# Click detection radii
CURSOR_HIT_RADIUS_CIRCLE = 20  # px — circle cursor click detection radius (fallback)
CURSOR_HIT_FRACTION = 0.05  # fraction of screen height for avatar cursor

# Cursor size limits (circle mode only)
CURSOR_SIZE_MIN = 1  # minimum circle cursor radius in pixels
CURSOR_SIZE_MAX = 50  # maximum circle cursor radius in pixels
CURSOR_DRAG_THRESHOLD = 5  # px size-delta below which a cursor press is treated as a click

# ---------------------------------------------------------------------------
# Wii Balance Board platform geometry
# Source: Leach et al. (2014) Sensors 14:18244-18267, doi:10.3390/s141018244, Figure 3.
# X = 433 mm (mediolateral sensor-to-sensor), Y = 238 mm (anteroposterior sensor-to-sensor)
# Half-distances in cm are used in the CoP formula (Leach et al. 2014, Equation 1):
#   CoP_ML_cm = WBB_SENSOR_DIST_ML_CM * (F_R - F_L) / F_total
#   CoP_AP_cm = WBB_SENSOR_DIST_AP_CM * (F_T - F_B) / F_total
# ---------------------------------------------------------------------------
WBB_SENSOR_DIST_ML_CM = 21.65  # X/2 = 433 mm / 2, in cm (mediolateral half-distance)
WBB_SENSOR_DIST_AP_CM = 11.9  # Y/2 = 238 mm / 2, in cm (anteroposterior half-distance)

# ---------------------------------------------------------------------------
# C# board library DLL — built by: cd WiiBalanceBoardLibrary && dotnet build
# ---------------------------------------------------------------------------
DLL_RELATIVE_PATH = os.path.join(
    "WiiBalanceBoardLibrary", "bin", "Debug", "net48", "WiiBalanceBoardLibrary.dll"
)
