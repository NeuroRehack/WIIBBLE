# main.py — WIIBBLE entry point
#
# Intentionally thin. All application logic lives in app.py.
# dpg context setup and argparse live here so other modules
# are safe to import in tests without side effects.

import argparse
import ctypes
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# ── Configure logging before any application imports ──────────────────────
_log_dir = Path.home() / ".wiibble"
_log_dir.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)-8s %(name)-20s %(message)s",
    handlers=[
        RotatingFileHandler(
            _log_dir / "wiibble.log",
            maxBytes=5 * 1024 * 1024,  # 5 MB per file
            backupCount=3,
            encoding="utf-8",
        ),
        logging.StreamHandler(sys.stdout),
    ],
)

log = logging.getLogger(__name__)

import dearpygui.dearpygui as dpg  # noqa: E402

from app import run  # noqa: E402
from state import AppState, Settings  # noqa: E402
from theme import apply_global_theme, load_fonts  # noqa: E402


def parse_args():
    """Parse command-line arguments for the WIIBBLE application."""
    parser = argparse.ArgumentParser(description="WIIBBLE - Wii Balance Board Live Environment")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run without physical hardware using simulated sensor data",
    )
    parser.add_argument(
        "--mock-scenario",
        type=str,
        default="sway",
        choices=["sway", "still", "lean_left", "lean_right", "hands", "step_on_off"],
        help="Simulation scenario (default: sway)",
    )
    return parser.parse_args()


def get_screen_size() -> tuple:
    """
    Get the primary monitor resolution using ctypes (no window creation,
    no Win32 message-loop side-effects that could interfere with DearPyGui).
    """
    user32 = ctypes.windll.user32
    # SM_CXSCREEN=0, SM_CYSCREEN=1
    w = user32.GetSystemMetrics(0)
    h = user32.GetSystemMetrics(1)
    log.debug("get_screen_size via ctypes: %dx%d", w, h)
    return w, h


if __name__ == "__main__":
    log.info("Starting WIIBBLE main entry point.")
    try:
        args = parse_args()
        log.debug("Args: %s", args)

        dpg.create_context()
        settings = Settings.load()
        screen_w, screen_h = get_screen_size()

        app_state = AppState(
            screen_width=screen_w,
            screen_height=screen_h * 0.9,  # leave room for taskbar
            historical_coords=[(0, 0)] * settings.trail_length,
        )

        # DPG init order: create_context → load_fonts → setup_dearpygui → create_viewport → show_viewport
        load_fonts()
        dpg.setup_dearpygui()
        apply_global_theme()

        dpg.create_viewport(
            title="WIIBBLE - Wii Balance Board Live Environment",
            width=screen_w,
            height=screen_h,
            x_pos=0,
            y_pos=0,
        )
        dpg.show_viewport()
        dpg.maximize_viewport()

        run(app_state, settings, args)
    except Exception:
        log.exception("Fatal exception in main")
    finally:
        dpg.destroy_context()
