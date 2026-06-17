"""Cross-platform display helpers for WIIBBLE entry points."""

import ctypes
import logging
import sys

log = logging.getLogger(__name__)

_DEFAULT_SCREEN_SIZE = (1280, 720)


def get_screen_size() -> tuple[int, int]:
    """
    Return primary monitor (width, height) in pixels.

    Windows uses ctypes to avoid creating a window before Dear PyGui starts.
    Other platforms use a hidden tkinter root; falls back to 1280x720.
    """
    if sys.platform == "win32":
        user32 = ctypes.windll.user32
        w = user32.GetSystemMetrics(0)
        h = user32.GetSystemMetrics(1)
        log.debug("get_screen_size via ctypes: %dx%d", w, h)
        return w, h

    try:
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        w = root.winfo_screenwidth()
        h = root.winfo_screenheight()
        root.destroy()
        log.debug("get_screen_size via tkinter: %dx%d", w, h)
        return w, h
    except Exception:
        log.warning(
            "Could not detect screen size; using default %dx%d",
            *_DEFAULT_SCREEN_SIZE,
        )
        return _DEFAULT_SCREEN_SIZE
