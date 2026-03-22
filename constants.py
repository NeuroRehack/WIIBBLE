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
# C# board library DLL — built by: cd WiiBalanceBoardLibrary && dotnet build
# ---------------------------------------------------------------------------
DLL_RELATIVE_PATH = os.path.join(
    "WiiBalanceBoardLibrary", "bin", "Debug", "net48", "WiiBalanceBoardLibrary.dll"
)
