"""Launch the THRIVE companion process from the live app."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

from wiibble.thrive.config import (
    DEFAULT_BROKER_HOST,
    DEFAULT_BROKER_PORT,
    DEFAULT_COMMAND_PORT,
    DEFAULT_FRAME_PORT,
    DEFAULT_HUB_ID,
    DEFAULT_NODE_ID,
)

log = logging.getLogger(__name__)

THRIVE_EXE_NAME = "WIIBBLE-THRIVE.exe"
THRIVE_SUBDIR = "thrive"

try:
    _compiled = bool(__compiled__)  # type: ignore[name-defined]  # noqa: F821
except NameError:
    _compiled = False


def _is_standalone_app() -> bool:
    return getattr(sys, "frozen", False) or _compiled


def resolve_thrive_command() -> list[str] | None:
    """Return argv prefix to run the THRIVE companion, or None if unavailable."""
    if _is_standalone_app():
        exe_dir = Path(sys.executable).resolve().parent
        companion = exe_dir / THRIVE_SUBDIR / THRIVE_EXE_NAME
        if not companion.is_file():
            log.error(
                "THRIVE companion not found: %s (expected next to %s)",
                companion,
                sys.executable,
            )
            return None
        return [str(companion)]

    return [sys.executable, "-m", "wiibble.thrive"]


def launch_thrive_companion_async(
    *,
    broker_host: str = DEFAULT_BROKER_HOST,
    broker_port: int = DEFAULT_BROKER_PORT,
    hub_id: str = DEFAULT_HUB_ID,
    node_id: str = DEFAULT_NODE_ID,
    frame_port: int = DEFAULT_FRAME_PORT,
    command_port: int = DEFAULT_COMMAND_PORT,
) -> subprocess.Popen | None:
    """Start the THRIVE MQTT companion without blocking the UI thread."""
    command = resolve_thrive_command()
    if command is None:
        return None

    args = [
        *command,
        "--broker-host",
        broker_host,
        "--broker-port",
        str(broker_port),
        "--hub-id",
        hub_id,
        "--node-id",
        node_id,
        "--frame-port",
        str(frame_port),
        "--command-port",
        str(command_port),
    ]

    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]

    log.info("Launching THRIVE companion: %s", " ".join(args))
    return subprocess.Popen(
        args,
        creationflags=creationflags,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
