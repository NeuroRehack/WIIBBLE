"""Launch the session-report companion process from the live app."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

log = logging.getLogger(__name__)

SESSION_REPORT_EXE_NAME = "WIIBBLE-SessionReport.exe"

try:
    _compiled = bool(__compiled__)  # type: ignore[name-defined]  # noqa: F821
except NameError:
    _compiled = False


def _is_standalone_app() -> bool:
    return getattr(sys, "frozen", False) or _compiled


def resolve_session_report_command() -> list[str] | None:
    """Return argv prefix to run session report, or None if unavailable."""
    if _is_standalone_app():
        exe_dir = Path(sys.executable).resolve().parent
        companion = exe_dir / SESSION_REPORT_EXE_NAME
        if not companion.is_file():
            log.error(
                "Session report companion not found: %s (expected next to %s)",
                companion,
                sys.executable,
            )
            return None
        return [str(companion)]

    return [sys.executable, "-m", "wiibble.cli.session_report"]


def launch_session_report_async(
    csv_path: str,
    *,
    open_browser: bool = True,
) -> subprocess.Popen | None:
    """Start session report generation without blocking the UI thread."""
    command = resolve_session_report_command()
    if command is None:
        return None

    open_flag = "--open" if open_browser else "--no-open"
    args = [*command, open_flag, str(csv_path)]

    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]

    log.info("Launching session report: %s", " ".join(args))
    return subprocess.Popen(
        args,
        creationflags=creationflags,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
