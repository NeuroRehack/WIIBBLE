# resources.py
import logging
import os
import sys

log = logging.getLogger(__name__)


def resource_path(relative_path: str) -> str:
    """
    Resolve a path to a bundled resource.
    Works in development (relative to repo root) and when compiled with
    Nuitka standalone (resources sit alongside the exe).
    """
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
        log.debug("resource_path: frozen (Nuitka), using exe dir = %s", base)
    else:
        base = os.path.abspath(".")
        log.debug("resource_path: dev mode, using cwd = %s", base)
    path = os.path.join(base, relative_path)
    if not os.path.exists(path):
        log.warning("Resource not found: %s", path)
    else:
        log.debug("Resource found: %s", path)
    return path


# Pre-resolved asset paths
FA_SOLID_FONT_PATH = resource_path("assets/fonts/fa-solid-900.ttf")

# Pre-resolved image paths — imported by any module that needs them
ICON_PATH = resource_path("images/logo.png")
PERSON_IMAGE_PATH = resource_path("images/logoPerson.png")
IMAGE_PATHS = [resource_path(f"images/wii{i}.png") for i in range(3)]
CONNECTION_PATH = resource_path("images/connection.png")
