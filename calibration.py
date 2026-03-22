# calibration.py
import dearpygui.dearpygui as dpg
from constants import TARE_MAX_WEIGHT
from data_processing import measure_weight
from ui import draw_step_instruction, ensure_textures_loaded


def wait_for_tare(device, dl, app_state) -> float:
    """
    Show 'Step OFF' screen and wait until the board is stable and empty.

    Passes when 20 consecutive readings are stable (delta < 1 kg) and
    below TARE_MAX_WEIGHT. Returns stable empty weight.
    """
    ensure_textures_loaded()
    baseline  = measure_weight(device, app_state.data_struct)
    last_w    = baseline
    counter   = 0
    max_count = 20

    while counter < max_count:
        if not dpg.is_dearpygui_running():
            return -1

        weight = measure_weight(device, app_state.data_struct)

        if abs(weight - last_w) < 1 and weight < TARE_MAX_WEIGHT:
            counter += 1
        else:
            counter = 0
            last_w  = weight

        # Redraw calibration screen
        dpg.delete_item(dl, children_only=True)
        draw_step_instruction(dl, "off", counter, max_count, app_state)
        dpg.render_dearpygui_frame()

    return weight


def sensitivity_calibration(device, dl, app_state, on_start=None) -> float:
    """
    Show 'Step ON' screen and wait until stable body weight is detected.

    Baseline measured first (board empty), then on_start() called.
    Passes when 20 consecutive readings stable and > baseline + 20 kg.
    Returns calibrated body weight.
    """
    ensure_textures_loaded()
    baseline = measure_weight(device, app_state.data_struct)

    if on_start:
        on_start()

    last_w    = baseline
    counter   = 0
    max_count = 20

    while counter < max_count:
        if not dpg.is_dearpygui_running():
            return -1

        weight = measure_weight(device, app_state.data_struct)

        if abs(weight - last_w) < 1 and (weight - baseline) > 20:
            counter += 1
        else:
            counter = 0
            last_w  = weight

        dpg.delete_item(dl, children_only=True)
        draw_step_instruction(dl, "on", counter, max_count, app_state)
        dpg.render_dearpygui_frame()

    return weight