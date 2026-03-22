# data_processing.py
import numpy as np
from constants import SCALE_FACTOR, TARE_MAX_WEIGHT


def read_data(device):
    """Read a raw 32-byte HID report from the device."""
    try:
        return device.read(32)
    except Exception as e:
        print(f"Failed to read data: {e}")
        return None


def parse_data(data: list, data_struct: dict) -> dict:
    """
    Parse raw HID bytes into kg values per corner, applying tare offsets.

    Formula: corner_kg = (data[i] + data[i+1] / 255 - tare) * SCALE_FACTOR
    Indices i are defined in data_struct per corner (3, 5, 7, 9).
    """
    corners = {}
    for key, val in data_struct.items():
        raw_index = val["rawIndex"]
        tare      = val["tare"]
        corners[key] = round(
            (data[raw_index] + data[raw_index + 1] / 255 - tare) * SCALE_FACTOR, 2
        )
    return corners


def tare(device, data_struct: dict) -> None:
    """
    Record the empty-board baseline into data_struct tare values.
    Averages 10 readings to reduce noise.
    Board must be empty (no weight) when this is called.
    """
    print("Taring...")
    for val in data_struct.values():
        val["tare"] = 0

    i = 0
    while i < 10:
        data = device.read(32)
        if data:
            data = np.array(data)
            for val in data_struct.values():
                val["tare"] += data[val["rawIndex"]] + data[val["rawIndex"] + 1] / 255
            i += 1
            print("*" * i)

    for val in data_struct.values():
        val["tare"] /= 10
    print(f"Tare complete: {data_struct}")


def measure_weight(device, data_struct: dict) -> float:
    """
    Average 10 readings to get a stable total weight in kg.
    Tare offsets in data_struct are applied via parse_data().
    """
    weight_vals = [0.0, 0.0, 0.0, 0.0]
    for _ in range(10):
        data = read_data(device)
        if data:
            corners = parse_data(data, data_struct)
            for i, key in enumerate(corners.keys()):
                weight_vals[i] += corners[key]
    weight_vals = [v / 10 for v in weight_vals]
    return sum(weight_vals)


def calculate_coordinates(
    top_left: float,
    top_right: float,
    bottom_left: float,
    bottom_right: float,
    weight: float,
    screen_width: float,
    screen_height: float,
    zoom: float = 1.0,
) -> tuple:
    """
    Convert corner kg values to screen coordinates (pixels from centre).

    Divides by total body weight to normalise, then scales to screen size.
    zoom (S3) is applied as a multiplier — 1.0 preserves original behaviour.
    Guard against weight == 0 to avoid division by zero.
    """
    if weight == 0:
        return 0.0, 0.0

    top_left     /= -weight
    top_right    /= -weight
    bottom_left  /= -weight
    bottom_right /= -weight

    x = (top_left + bottom_left) / 2 - (top_right + bottom_right) / 2
    y = (top_left + top_right)   / 2 - (bottom_left + bottom_right) / 2

    x *= screen_width  * 0.9 * zoom
    y *= screen_height * 0.9 * zoom
    return x, y
