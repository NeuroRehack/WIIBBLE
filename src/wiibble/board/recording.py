"""CSV recording utilities for WIIBBLE.

This module is responsible for serializing recording buffers to timestamped
CSV files under the recordings directory.
"""

import csv
import datetime
import logging
import re
from pathlib import Path

log = logging.getLogger(__name__)

DEFAULT_RECORDING_PREFIX = "recording"
DEFAULT_RECORDING_DIR = Path.home() / "Documents" / "WIIBBLE" / "recordings"
RECORDING_PREFIX_MAX_LEN = 40
_INVALID_PREFIX_CHARS = re.compile(r"[^A-Za-z0-9_-]")
_WINDOWS_RESERVED_NAMES = frozenset(
    {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }
)


def _escape_windows_reserved_name(prefix: str) -> str:
    """Avoid Windows reserved device names by suffixing ``_file``."""
    if prefix.upper() in _WINDOWS_RESERVED_NAMES:
        return f"{prefix}_file"
    return prefix


def normalize_recording_prefix(prefix: str) -> str:
    """Normalize a user-supplied recording filename prefix.

    - Strips leading/trailing whitespace
    - Replaces spaces with underscores
    - Strips leading dots
    - Removes characters other than letters, digits, ``_``, and ``-``
    - Collapses repeated underscores
    - Escapes Windows reserved device names
    - Truncates to :data:`RECORDING_PREFIX_MAX_LEN` characters
    """
    if not prefix:
        return ""
    text = prefix.strip().replace(" ", "_").lstrip(".")
    text = _INVALID_PREFIX_CHARS.sub("", text)
    text = re.sub(r"_+", "_", text).strip("_")
    text = _escape_windows_reserved_name(text)
    return text[:RECORDING_PREFIX_MAX_LEN]


def build_recording_filename(prefix: str, start_time: datetime.datetime) -> str:
    """Build a recording CSV filename from prefix and recording start time."""
    effective = normalize_recording_prefix(prefix) or DEFAULT_RECORDING_PREFIX
    timestamp = start_time.strftime("%y%m%d%H%M%S")
    return f"{effective}_{timestamp}.csv"


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
    """Save the provided recording buffer to a timestamped CSV file.

    The recorded values are always raw (unfiltered) corner force deviations.
    ``ui_filter_window`` is stored as provenance metadata only — it describes
    the smoothing that was applied to the *display* cursor, not to the data.

    Metadata is written as comment lines (prefixed with ``#``) before the CSV
    header so it can be recovered by the analysis pipeline without breaking
    standard CSV readers that skip unknown lines.

    Returns the absolute path of the written file.
    """
    if not out_dir:
        out_path = DEFAULT_RECORDING_DIR
    else:
        out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    if start_time is None:
        start_time = datetime.datetime.now()
    filename = build_recording_filename(prefix, start_time)
    path = _resolve_recording_path(out_path, filename)
    with path.open("w", newline="") as f:
        # Metadata comments — parsed by analysis.load_recording()
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
