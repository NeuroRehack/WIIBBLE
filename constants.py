# constants.py

# Hardware identifiers
VENDOR_ID = 0x057e        # Nintendo Co., Ltd
PRODUCT_ID = 0x0306       # Wii Balance Board

# HID report byte indices for each corner sensor
# Format: data[i] = integer part, data[i+1] = fractional part (/255)
SENSOR_INDICES = {
    "top_right":    3,
    "bottom_right": 5,
    "top_left":     7,
    "bottom_left":  9,
}

# Empirically derived kg calibration factor for raw HID byte values
# raw_kg = (data[i] + data[i+1] / 255) * SCALE_FACTOR
SCALE_FACTOR = 2.6441910428028423

# Maximum board capacity threshold used in wait_for_tare()
# Board reports ~530 raw kg-equivalent when overloaded; anything below
# this is considered "board is empty enough to tare"
TARE_MAX_WEIGHT = 530

# DLL path for C# board library
import os
DLL_RELATIVE_PATH = os.path.join(
    'WiiBalanceBoardLibrary', 'bin', 'Debug', 'net48', 'WiiBalanceBoardLibrary.dll'
)
