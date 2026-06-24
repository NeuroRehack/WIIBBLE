"""CSV recording utilities for WIIBBLE."""

from __future__ import annotations

import csv
import datetime
import logging
from pathlib import Path

from wiibble.utils.recording_names import (
    build_recording_filename,
    normalize_recording_prefix,
    resolve_recording_dir,
)

log = logging.getLogger(__name__)

__all__ = [
    "_save_recording_csv",
    "build_recording_filename",
    "normalize_recording_prefix",
    "resolve_recording_dir",
]


def _resolve_recording_path(out_dir: Path, filename: str) -> Path:
    """Return a writable path, appending ``_2``, ``_3``, … when *filename* exists."""
    path = out_dir / filename
    if not path.exists():
        return path
    stem = Path(filename).stem
    ext = Path(filename).suffix
    suffix = 2
    while True:
        candidate = out_dir / f"{stem}_{suffix}{ext}"
        if not candidate.exists():
            return candidate
        suffix += 1


def _save_recording_csv(
    record_buffer,
    total_weight_kg: float = None,
    ui_filter_window: int = 1,
    out_dir: str = "",
    flip_horizontal: bool = False,
    flip_vertical: bool = False,
    prefix: str = "",
    start_time: datetime.datetime | None = None,
) -> str:
    """Save the provided recording buffer to a timestamped CSV file."""
    out_path = resolve_recording_dir(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    if start_time is None:
        start_time = datetime.datetime.now()
    filename = build_recording_filename(prefix, start_time)
    path = _resolve_recording_path(out_path, filename)
    with path.open("w", newline="") as f:
        if total_weight_kg is not None:
            f.write(f"# total_weight_kg={total_weight_kg:.4f}\n")
        f.write(f"# ui_filter_window={ui_filter_window}\n")
        f.write(f"# flip_horizontal={str(flip_horizontal).lower()}\n")
        f.write(f"# flip_vertical={str(flip_vertical).lower()}\n")
        writer = csv.writer(f)
        writer.writerow(["time (s)", "x (kg)", "y (kg)"])
        for row in record_buffer:
            writer.writerow([f"{row[0]:.3f}", f"{row[1]:.3f}", f"{row[2]:.3f}"])
    log.info("Recording saved to %s", path)
    return str(path)
