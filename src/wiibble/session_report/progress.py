"""Sidecar JSON progress file for async session-report generation."""

from __future__ import annotations

import json
import logging
import sys
import time
from contextlib import suppress
from dataclasses import asdict, dataclass
from pathlib import Path

from wiibble.utils.recording_names import recording_stem

log = logging.getLogger(__name__)

__all__ = [
    "ProgressSnapshot",
    "ReportProgressWriter",
    "progress_path_for",
    "read_report_progress",
    "remove_report_progress_file",
]

_WRITE_RETRIES = 8
_WRITE_RETRY_DELAY_S = 0.02
_CLEAR_RETRIES = 8


def progress_path_for(csv_path: Path | str) -> Path:
    """Return the progress JSON sidecar path for a recording CSV."""
    csv = Path(csv_path)
    return csv.with_name(f"{recording_stem(csv)}.report_progress.json")


@dataclass(frozen=True)
class ProgressSnapshot:
    """Point-in-time session-report progress."""

    label: str
    step: int
    total: int
    pct: float

    def as_dict(self) -> dict:
        return asdict(self)


def _atomic_write_text(path: Path, payload: str) -> None:
    """Write *payload* to *path*, retrying replace races on Windows."""
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    last_error: OSError | None = None

    for attempt in range(_WRITE_RETRIES):
        try:
            tmp_path.write_text(payload, encoding="utf-8")
            tmp_path.replace(path)
            return
        except OSError as exc:
            last_error = exc
            with suppress(OSError):
                tmp_path.unlink(missing_ok=True)
            time.sleep(_WRITE_RETRY_DELAY_S * (attempt + 1))

    if sys.platform == "win32":
        # Fall back to in-place write — readers tolerate partial JSON briefly.
        try:
            path.write_text(payload, encoding="utf-8")
            with suppress(OSError):
                tmp_path.unlink(missing_ok=True)
            return
        except OSError as exc:
            last_error = exc

    if last_error is not None:
        raise last_error


class ReportProgressWriter:
    """Write step-based progress to a sidecar JSON file for the main app."""

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)
        self._total = 1
        self._step = 0
        self._label = "Starting..."

    @property
    def path(self) -> Path:
        return self._path

    def configure(self, total: int, label: str = "Starting...") -> None:
        """Set the step budget and write the initial snapshot."""
        self._total = max(1, total)
        self._step = 0
        self._label = label
        self._write()

    def advance(self, label: str) -> None:
        """Increment the step counter and write a new snapshot."""
        self._step = min(self._step + 1, self._total)
        self._label = label
        self._write()

    def clear(self) -> None:
        """Remove the sidecar progress file (best-effort)."""
        remove_report_progress_file(self._path)

    def _write(self) -> None:
        snapshot = ProgressSnapshot(
            label=self._label,
            step=self._step,
            total=self._total,
            pct=self._step / self._total,
        )
        payload = json.dumps(snapshot.as_dict(), ensure_ascii=False)
        try:
            _atomic_write_text(self._path, payload)
        except OSError:
            log.warning(
                "Could not update report progress file: %s",
                self._path,
                exc_info=True,
            )


def remove_report_progress_file(path: Path | str) -> None:
    """Delete a progress sidecar file, retrying Windows sharing races."""
    file_path = Path(path)
    for attempt in range(_CLEAR_RETRIES):
        if not file_path.is_file():
            return
        try:
            file_path.unlink()
            return
        except OSError:
            time.sleep(_WRITE_RETRY_DELAY_S * (attempt + 1))

    tmp_path = file_path.with_suffix(file_path.suffix + ".tmp")
    with suppress(OSError):
        tmp_path.unlink(missing_ok=True)


def read_report_progress(path: Path | str) -> ProgressSnapshot | None:
    """Read the latest progress snapshot, or None if missing or invalid."""
    file_path = Path(path)
    if not file_path.is_file():
        return None

    for attempt in range(2):
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            return ProgressSnapshot(
                label=str(data.get("label", "")),
                step=int(data.get("step", 0)),
                total=max(1, int(data.get("total", 1))),
                pct=float(data.get("pct", 0.0)),
            )
        except json.JSONDecodeError:
            if attempt == 0:
                time.sleep(_WRITE_RETRY_DELAY_S)
                continue
            return None
        except (OSError, TypeError, ValueError):
            return None
    return None
