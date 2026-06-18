"""Resolve bundled asset paths for development and Nuitka standalone builds."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

log = logging.getLogger(__name__)

try:
    _compiled = bool(__compiled__)  # type: ignore[name-defined]  # noqa: F821
except NameError:
    _compiled = False


def resource_path(relative_path: str) -> str:
    """Resolve a path to a bundled resource.

    Works in development (relative to repo root) and when compiled with
    Nuitka standalone (resources sit alongside the exe).

    Args:
        relative_path: Path relative to the project or executable root.

    Returns:
        Absolute path string to the resource.
    """
    if getattr(sys, "frozen", False) or _compiled:
        base = Path(sys.executable).resolve().parent
        log.debug("resource_path: standalone build, using exe dir = %s", base)
    else:
        base = Path.cwd().resolve()
        log.debug("resource_path: dev mode, using cwd = %s", base)
    path = base / relative_path
    if not path.is_file():
        log.warning("Resource not found: %s", path)
    else:
        log.debug("Resource found: %s", path)
    return str(path)


FA_SOLID_FONT_PATH = resource_path("assets/fonts/fa-solid-900.ttf")
ICON_PATH = resource_path("images/logo.png")
PERSON_IMAGE_PATH = resource_path("images/logoPerson.png")
IMAGE_PATHS = [resource_path(f"images/wii{i}.png") for i in range(3)]
CONNECTION_PATH = resource_path("images/connection.png")
