"""End-of-session posturographic report orchestration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from wiibble.session_report.launcher import (
    SESSION_REPORT_EXE_NAME,
    launch_session_report_async,
    open_report_in_browser,
    resolve_session_report_command,
)

if TYPE_CHECKING:
    from wiibble.session_report.runner import run_session_report

__all__ = [
    "SESSION_REPORT_EXE_NAME",
    "launch_session_report_async",
    "open_report_in_browser",
    "resolve_session_report_command",
    "run_session_report",
]


def __getattr__(name: str) -> Any:
    # Lazily expose run_session_report without importing the heavy analysis/
    # plotly stack at package import time (keeps it out of the main exe build).
    if name == "run_session_report":
        from wiibble.session_report.runner import run_session_report

        return run_session_report
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
