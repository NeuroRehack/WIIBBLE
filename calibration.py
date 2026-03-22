# calibration.py
import numpy as np
import pygame
from constants import TARE_MAX_WEIGHT
from data_processing import measure_weight
from resources import IMAGE_PATHS
from ui import show_step_instruction, display_message


def wait_for_tare(device, screen, app_state) -> float:
    """
    Show 'Step OFF' screen and wait until the board is stable and empty.

    Passes when 20 consecutive readings are stable (delta < 1 kg) and
    below TARE_MAX_WEIGHT — meaning the board is empty and settled.
    Returns the stable empty weight (should be near zero after tare).
    """
    images    = [pygame.image.load(p) for p in IMAGE_PATHS]
    baseline  = measure_weight(device, app_state.data_struct)
    last_w    = baseline
    counter   = 0
    max_count = 20
    sw, sh    = app_state.screen_width, app_state.screen_height

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                device.close()
                return -1

        weight = measure_weight(device, app_state.data_struct)

        if counter == max_count:
            break

        if abs(weight - last_w) < 1 and weight < TARE_MAX_WEIGHT:
            counter += 1
        else:
            counter = 0
            last_w  = weight

        show_step_instruction(screen, images[2], "off", app_state)
        pygame.draw.arc(
            screen, (250, 0, 0),
            (sw * 0.54, sh * 0.2, sh // 2, sh // 2),
            0, 2 * np.pi * counter / max_count, 10,
        )
        pygame.display.flip()

    return weight


def sensitivity_calibration(device, screen, app_state, on_start=None) -> float:
    """
    Show 'Step ON' screen and wait until stable body weight is detected.

    Baseline is measured first (board empty), then on_start() is called
    (switches mock to on-board phase, or is a no-op for real hardware).
    Passes when 20 consecutive readings are stable and > baseline + 20 kg.
    Returns the stable body weight used to calibrate coordinate scaling.
    """
    images    = [pygame.image.load(p) for p in IMAGE_PATHS]
    baseline  = measure_weight(device, app_state.data_struct)

    if on_start:
        on_start()

    last_w    = baseline
    counter   = 0
    max_count = 20
    sw, sh    = app_state.screen_width, app_state.screen_height

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                device.close()
                return -1

        weight = measure_weight(device, app_state.data_struct)

        if counter == max_count:
            break

        if abs(weight - last_w) < 1 and (weight - baseline) > 20:
            counter += 1
        else:
            counter = 0
            last_w  = weight

        show_step_instruction(screen, images[2], "on", app_state)
        pygame.draw.arc(
            screen, (0, 250, 0),
            (sw * 0.54, sh * 0.2, sh // 2, sh // 2),
            0, 2 * np.pi * counter / max_count, 10,
        )
        pygame.display.flip()

    return weight
