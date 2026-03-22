# main.py — WIIBBLE entry point
#
# This file is intentionally thin. All application logic lives in app.py.
# Keeping pygame.init() and argparse here (not at module level in other files)
# means imports are safe to use in tests without side effects.

import argparse
import pygame
from state import AppState, Settings
from app   import run


def parse_args():
    parser = argparse.ArgumentParser(description="WIIBBLE - Wii Balance Board Live Environment")
    parser.add_argument(
        "--mock", action="store_true",
        help="Run without physical hardware using simulated sensor data",
    )
    parser.add_argument(
        "--mock-scenario", type=str, default="sway",
        choices=["sway", "still", "lean_left", "lean_right", "hands"],
        help="Simulation scenario (default: sway)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    pygame.init()
    pygame.mixer.quit()  # no audio hardware in most deployment environments

    info = pygame.display.Info()
    settings  = Settings()
    app_state = AppState(
        screen_width=info.current_w,
        screen_height=info.current_h * 0.9,
        historical_coords=[(0, 0)] * settings.trail_length,
    )

    run(app_state, settings, args)
    pygame.quit()
