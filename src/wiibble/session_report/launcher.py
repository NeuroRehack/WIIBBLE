"""Launch the session-report companion process from the live app."""

from __future__ import annotations

import logging
import os
import platform
import subprocess
import sys
import webbrowser
from pathlib import Path

log = logging.getLogger(__name__)


def parse_session_report_stdout(stdout: str) -> str:
    """Extract the HTML report path printed by the session-report subprocess."""
    for line in reversed(stdout.splitlines()):
        stripped = line.strip()
        if stripped.lower().endswith(".html"):
            return stripped
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    return lines[-1] if lines else ""


def open_report_in_browser(report_path: Path) -> None:
    """Open an HTML report in the system default browser.

    Lives here (not in ``runner``) so the main app can open reports without
    importing the heavy analysis/plotly stack that ``runner`` depends on.
    """
    path = report_path.resolve()
    if platform.system() == "Windows":
        os.startfile(path)  # noqa: S606
    else:
        webbrowser.open(path.as_uri())


SESSION_REPORT_EXE_NAME = "WIIBBLE-SessionReport.exe"
SESSION_REPORT_SUBDIR = "session_report"

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
        companion = exe_dir / SESSION_REPORT_SUBDIR / SESSION_REPORT_EXE_NAME
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
