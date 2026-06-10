# data_processing.py
import logging

import numpy as np

from wiibble.utils.constants import COORD_SCALE, SCALE_FACTOR

log = logging.getLogger(__name__)


def calculate_force_deviation_kg(
    top_left: float, top_right: float, bottom_left: float, bottom_right: float
) -> tuple:
    """
    Calculate x and y force deviations (in kg) from the four corner sensor readings.
    x: Net left-right force (kg), positive = more weight on right, negative = more on left
    y: Net front-back force (kg), positive = more weight forward, negative = more backward
    Returns (x, y) in kg.
    """
    # x axis: right sensors minus left sensors
    x = (top_right + bottom_right) - (top_left + bottom_left)
    # y axis: front sensors (top) minus back sensors (bottom)
    y = (top_left + top_right) - (bottom_left + bottom_right)
    return x, y


def read_data(device):
    """Read a raw 32-byte HID report from the device."""
    try:
        return device.read(32)
    except Exception as e:
        log.warning("Failed to read data: %s", e)
        return None


def read_latest_data(device) -> tuple:
    """Drain the HID input buffer and return the most recent 32-byte report.

    In non-blocking mode the OS may queue multiple reports between render
    frames. Reading only once per frame processes stale (FIFO) data and can
    add hundreds of milliseconds of display lag. This function reads until
    the buffer is empty and keeps the last report.

    Returns:
        (data, reports_drained): ``data`` is the latest report or None if no
        report was available; ``reports_drained`` is how many reports were
        consumed (0 when ``data`` is None).
    """
    latest = None
    reports_drained = 0
    while True:
        try:
            data = device.read(32)
        except Exception as e:
            log.warning("Failed to read data: %s", e)
            break
        if not data:
            break
        latest = data
        reports_drained += 1
    return latest, reports_drained


def parse_data(data: list, data_struct: dict) -> dict:
    """
    Parse raw HID bytes into kg values per corner, applying tare offsets.

    Formula: corner_kg = (data[i] + data[i+1] / 255 - tare) * SCALE_FACTOR
    Indices i are defined in data_struct per corner (3, 5, 7, 9).
    """
    corners = {}
    for key, val in data_struct.items():
        raw_index = val["rawIndex"]
        tare = val["tare"]
        corners[key] = round((data[raw_index] + data[raw_index + 1] / 255 - tare) * SCALE_FACTOR, 2)
    return corners


def tare(device, data_struct: dict) -> None:
    """
    Record the empty-board baseline into data_struct tare values.
    Averages 10 readings to reduce noise.
    Board must be empty (no weight) when this is called.
    """
    log.debug("Taring...")
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

    for val in data_struct.values():
        val["tare"] /= 10
    log.debug("Tare complete: %s", data_struct)


def measure_weight(device, data_struct: dict) -> float:
    """
    Average 10 readings to get a stable total weight in kg.
    Tare offsets in data_struct are applied via parse_data().
    """
    weight_vals = [0.0, 0.0, 0.0, 0.0]
    n = 0
    for _ in range(10):
        data = read_data(device)
        if data:
            corners = parse_data(data, data_struct)
            for i, key in enumerate(corners.keys()):
                weight_vals[i] += corners[key]
            n += 1
    if n == 0:
        return 0.0
    weight_vals = [v / n for v in weight_vals]
    return sum(weight_vals)


def apply_filter(corners: dict, filter_buffer: list, filter_window: int) -> dict:
    """
    Apply a moving average filter to raw corner kg values.

    Appends the new corners reading to filter_buffer (in-place), trims it to
    filter_window length, then returns the mean of each corner across the buffer.

    filter_window=1 is a pass-through — no smoothing, no latency.
    Filtering at the sensor level (before coordinate calculation) suppresses
    ADC noise before it gets amplified by the coordinate scaling step.

    Args:
        corners:       dict of {corner_name: kg_value} from parse_data()
        filter_buffer: mutable list stored in app_state — modified in-place
        filter_window: number of frames to average (from settings.filter_window)

    Returns:
        dict of smoothed corner kg values with the same keys as corners
    """
    filter_buffer.append(corners)
    if len(filter_buffer) > filter_window:
        filter_buffer.pop(0)
    n = len(filter_buffer)
    return {key: sum(frame[key] for frame in filter_buffer) / n for key in corners}


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

    top_left /= -weight
    top_right /= -weight
    bottom_left /= -weight
    bottom_right /= -weight

    x = (top_left + bottom_left) / 2 - (top_right + bottom_right) / 2
    y = (top_left + top_right) / 2 - (bottom_left + bottom_right) / 2

    x *= screen_width * COORD_SCALE * zoom
    y *= screen_height * COORD_SCALE * zoom
    return x, y
