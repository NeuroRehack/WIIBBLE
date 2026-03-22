# resources.py
import os
import sys


def resource_path(relative_path: str) -> str:
    """
    Resolve a path to a bundled resource.
    Works both in development (relative to repo root) and when packaged
    with PyInstaller (which extracts resources to sys._MEIPASS).
    """
    try:
        base = sys._MEIPASS
    except AttributeError:
        base = os.path.abspath(".")
    path = os.path.join(base, relative_path)
    if not os.path.exists(path):
        print(f"[WARN] Resource not found: {path}")
    return path


# Pre-resolved image paths — imported by any module that needs them
ICON_PATH         = resource_path("images/logo.png")
PERSON_IMAGE_PATH = resource_path("images/logoPerson.png")
IMAGE_PATHS       = [resource_path(f"images/wii{i}.png") for i in range(3)]
CONNECTION_PATH   = resource_path("images/connection.png")
