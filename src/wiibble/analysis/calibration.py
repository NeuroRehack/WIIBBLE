# calibration.py
import logging
from collections.abc import Callable

import dearpygui.dearpygui as dpg

from wiibble.features.data_processing import (
    compute_scale_factor,
    measure_raw_load,
    measure_weight,
    tare,
)
from wiibble.ui.ui import (
    draw_reference_weight_instruction,
    draw_step_instruction,
    ensure_textures_loaded,
)
from wiibble.utils.constants import CALIB_MIN_WEIGHT_DELTA, RAW_STABILITY_DELTA, TARE_MAX_WEIGHT

log = logging.getLogger(__name__)


def _with_blocking_reads(device, fn: Callable) -> object:
    """Run a calibration routine with blocking HID reads; restore non-blocking after."""
    restore_nonblocking = False
    if hasattr(device, "set_nonblocking"):
        device.set_nonblocking(0)
        restore_nonblocking = True
    try:
        return fn()
    finally:
        if hasattr(device, "enter_running_mode"):
            device.enter_running_mode()
        if restore_nonblocking:
            device.set_nonblocking(1)


def wait_for_tare(device, dl, app_state, scale_factor: float) -> float:
    """
    Show 'Step OFF' screen and wait until the board is stable and empty.

    Passes when 20 consecutive readings are stable (delta < 1 kg) and
    below TARE_MAX_WEIGHT. Returns stable empty weight.
    """
    log.debug("wait_for_tare: waiting for stable empty board...")
    ensure_textures_loaded()
    baseline = measure_weight(device, app_state.data_struct, scale_factor)
    last_w = baseline
    counter = 0
    max_count = 20

    while counter < max_count:
        if not dpg.is_dearpygui_running():
            log.warning("wait_for_tare: aborted — window closed.")
            return -1

        weight = measure_weight(device, app_state.data_struct, scale_factor)

        if abs(weight - last_w) < 1 and weight < TARE_MAX_WEIGHT:
            counter += 1
        else:
            counter = 0
            last_w = weight

        dpg.delete_item(dl, children_only=True)
        draw_step_instruction(dl, "off", counter, max_count, app_state)
        dpg.render_dearpygui_frame()

    log.info("wait_for_tare: stable empty board — baseline weight %.3f kg", weight)
    return weight


def sensitivity_calibration(device, dl, app_state, scale_factor: float, on_start=None) -> float:
    """
    Show 'Step ON' screen and wait until stable body weight is detected.

    Baseline measured first (board empty), then on_start() called.
    Passes when 20 consecutive readings stable and > baseline + CALIB_MIN_WEIGHT_DELTA kg.
    Returns calibrated body weight.
    """
    log.debug("sensitivity_calibration: waiting for subject to step on...")
    ensure_textures_loaded()
    baseline = measure_weight(device, app_state.data_struct, scale_factor)

    if on_start:
        on_start()

    last_w = baseline
    counter = 0
    max_count = 20

    while counter < max_count:
        if not dpg.is_dearpygui_running():
            log.warning("sensitivity_calibration: aborted — window closed.")
            return -1

        weight = measure_weight(device, app_state.data_struct, scale_factor)

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


def reference_weight_scale_calibration(
    device,
    dl,
    app_state,
    reference_kg: float,
    scale_factor: float,
    on_start=None,
) -> float:
    """
    Wait until a known reference mass is placed stably on the board.

    Returns the new scale_factor, or -1 if aborted.
    """
    log.debug(
        "reference_weight_scale_calibration: waiting for %.2f kg reference load...",
        reference_kg,
    )
    ensure_textures_loaded()
    baseline_raw = measure_raw_load(device, app_state.data_struct)

    if on_start:
        on_start()

    min_raw_delta = reference_kg / scale_factor * 0.5 if scale_factor > 0 else 1.0
    last_raw = baseline_raw
    counter = 0
    max_count = 20
    raw_load = baseline_raw

    while counter < max_count:
        if not dpg.is_dearpygui_running():
            log.warning("reference_weight_scale_calibration: aborted — window closed.")
            return -1

        raw_load = measure_raw_load(device, app_state.data_struct)

        if (
            abs(raw_load - last_raw) < RAW_STABILITY_DELTA
            and (raw_load - baseline_raw) > min_raw_delta
        ):
            counter += 1
        else:
            counter = 0
            last_raw = raw_load

        dpg.delete_item(dl, children_only=True)
        draw_reference_weight_instruction(dl, reference_kg, counter, max_count, app_state)
        dpg.render_dearpygui_frame()

    try:
        new_factor = compute_scale_factor(reference_kg, raw_load)
    except ValueError:
        log.exception("reference_weight_scale_calibration: invalid raw load")
        return -1

    log.info(
        "reference_weight_scale_calibration: scale_factor = %.6f (raw_load=%.4f)",
        new_factor,
        raw_load,
    )
    return new_factor


def run_board_weight_calibration(device, dl, app_state, scale_factor: float) -> float:
    """
    Full on-board weight calibration: empty-board wait → tare → step-on measurement.

    Returns calibrated body weight in kg, or -1 if aborted (window closed).
    """

    def _run() -> float:
        if hasattr(device, "reset_calibration_phase"):
            device.reset_calibration_phase()

        result = wait_for_tare(device, dl, app_state, scale_factor)
        if result == -1:
            return -1

        try:
            tare(device, app_state.data_struct)
        except Exception:
            log.exception("run_board_weight_calibration: tare failed")
            return -1

        on_start = device.trigger_step_on if hasattr(device, "trigger_step_on") else None
        return sensitivity_calibration(device, dl, app_state, scale_factor, on_start=on_start)

    return _with_blocking_reads(device, _run)


def run_board_scale_calibration(
    device, dl, app_state, reference_kg: float, scale_factor: float
) -> float:
    """
    Board scale calibration: tare → place reference mass → compute scale_factor.

    Returns new scale_factor, or -1 if aborted.
    """

    def _run() -> float:
        if hasattr(device, "reset_calibration_phase"):
            device.reset_calibration_phase()

        result = wait_for_tare(device, dl, app_state, scale_factor)
        if result == -1:
            return -1

        try:
            tare(device, app_state.data_struct)
        except Exception:
            log.exception("run_board_scale_calibration: tare failed")
            return -1

        on_start = None
        if hasattr(device, "trigger_reference_load"):

            def _trigger_reference() -> None:
                device.trigger_reference_load(reference_kg)

            on_start = _trigger_reference
        return reference_weight_scale_calibration(
            device,
            dl,
            app_state,
            reference_kg,
            scale_factor,
            on_start=on_start,
        )

    return _with_blocking_reads(device, _run)
