"""Central logging configuration for WIIBBLE entry points."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging(
    *,
    level: int = logging.INFO,
    log_to_file: bool = True,
    stream: bool = True,
) -> None:
    """Configure the root logger once for a WIIBBLE process.

    Args:
        level: Root log level.
        log_to_file: Write rotating logs under ``~/.wiibble/wiibble.log``.
        stream: Mirror logs to stdout.
    """
    handlers: list[logging.Handler] = []
    if log_to_file:
        log_dir = Path.home() / ".wiibble"
        log_dir.mkdir(exist_ok=True)
        handlers.append(
            RotatingFileHandler(
                log_dir / "wiibble.log",
                maxBytes=5 * 1024 * 1024,
                backupCount=3,
                encoding="utf-8",
            )
        )
    if stream:
        handlers.append(logging.StreamHandler(sys.stdout))

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)-20s %(message)s"
        if log_to_file
        else "%(levelname)s %(name)s: %(message)s",
        handlers=handlers,
        force=True,
    )


def install_uncaught_exception_hook(logger: logging.Logger | None = None) -> None:
    """Log unhandled exceptions before the process exits."""
    log = logger or logging.getLogger(__name__)

    def _hook(exc_type, exc_value, exc_tb) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        log.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_tb))

    sys.excepthook = _hook
