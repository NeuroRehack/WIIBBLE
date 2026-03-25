# main.py — WIIBBLE entry point
#
# Intentionally thin. All application logic lives in app.py.
# dpg context setup and argparse live here so other modules
# are safe to import in tests without side effects.

import argparse
import tkinter
import dearpygui.dearpygui as dpg

from state import AppState, Settings
from app   import run
from theme import load_fonts, apply_global_theme


def parse_args():
    parser = argparse.ArgumentParser(description="WIIBBLE - Wii Balance Board Live Environment")
    parser.add_argument(
        "--mock", action="store_true",
        help="Run without physical hardware using simulated sensor data",
    )
    parser.add_argument(
        "--mock-scenario", type=str, default="sway",
        choices=["sway", "still", "lean_left", "lean_right", "hands", "step_on_off"],
        help="Simulation scenario (default: sway)",
    )
    return parser.parse_args()


def get_screen_size() -> tuple:
    """
    Get the primary monitor resolution using tkinter (stdlib, no extra deps).
    Used to size the DPG viewport to fill the screen on startup.
    """
    root = tkinter.Tk()
    root.withdraw()  # hide the tkinter window immediately
    w = root.winfo_screenwidth()
    h = root.winfo_screenheight()
    root.destroy()
    return w, h


if __name__ == "__main__":
    args = parse_args()

    dpg.create_context()

    settings  = Settings.load()

    screen_w, screen_h = get_screen_size()
    app_state = AppState(
        screen_width=screen_w,
        screen_height=screen_h * 0.9,  # leave room for taskbar
        historical_coords=[(0, 0)] * settings.trail_length,
    )

    dpg.create_viewport(
        title="WIIBBLE - Wii Balance Board Live Environment",
        width=screen_w,
        height=screen_h,
        x_pos=0,
        y_pos=0,
    )
    load_fonts()          # must happen before setup_dearpygui()
    dpg.setup_dearpygui()
    apply_global_theme()  # colours/styles after setup
    dpg.show_viewport()
    dpg.maximize_viewport()

    run(app_state, settings, args)

    dpg.destroy_context()