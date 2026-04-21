# calibration.py
import logging

import dearpygui.dearpygui as dpg

from constants import CALIB_MIN_WEIGHT_DELTA, TARE_MAX_WEIGHT
from data_processing import measure_weight
from ui import draw_step_instruction, ensure_textures_loaded

log = logging.getLogger(__name__)


def wait_for_tare(device, dl, app_state) -> float:
    """
    Show 'Step OFF' screen and wait until the board is stable and empty.

    Passes when 20 consecutive readings are stable (delta < 1 kg) and
    below TARE_MAX_WEIGHT. Returns stable empty weight.
    """
    log.debug("wait_for_tare: waiting for stable empty board...")
    ensure_textures_loaded()
    baseline = measure_weight(device, app_state.data_struct)
    last_w = baseline
    counter = 0
    max_count = 20

    while counter < max_count:
        if not dpg.is_dearpygui_running():
            log.warning("wait_for_tare: aborted — window closed.")
            return -1

        weight = measure_weight(device, app_state.data_struct)

        if abs(weight - last_w) < 1 and weight < TARE_MAX_WEIGHT:
            counter += 1
        else:
            counter = 0
            last_w = weight

        # Redraw calibration screen
        dpg.delete_item(dl, children_only=True)
        draw_step_instruction(dl, "off", counter, max_count, app_state)
        dpg.render_dearpygui_frame()

    log.info("wait_for_tare: stable empty board — baseline weight %.3f kg", weight)
    return weight


def sensitivity_calibration(device, dl, app_state, on_start=None) -> float:
    """
    Show 'Step ON' screen and wait until stable body weight is detected.

    Baseline measured first (board empty), then on_start() called.
    Passes when 20 consecutive readings stable and > baseline + CALIB_MIN_WEIGHT_DELTA kg.
    Returns calibrated body weight.
    """
    log.debug("sensitivity_calibration: waiting for subject to step on...")
    ensure_textures_loaded()
    baseline = measure_weight(device, app_state.data_struct)

    if on_start:
        on_start()

    last_w = baseline
    counter = 0
    max_count = 20

    while counter < max_count:
        if not dpg.is_dearpygui_running():
            log.warning("sensitivity_calibration: aborted — window closed.")
            return -1

        weight = measure_weight(device, app_state.data_struct)

        if abs(weight - last_w) < 1 and (weight - baseline) > CALIB_MIN_WEIGHT_DELTA:
            counter += 1
        else:
            counter = 0
            last_w = weight

        dpg.delete_item(dl, children_only=True)
        draw_step_instruction(dl, "on", counter, max_count, app_state)
        dpg.render_dearpygui_frame()

    log.info("sensitivity_calibration: calibrated body weight = %.2f kg", weight)
    return weight
