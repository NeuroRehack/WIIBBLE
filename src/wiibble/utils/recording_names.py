"""Recording filename and path helpers (no I/O)."""

from __future__ import annotations

import datetime
import re
from pathlib import Path

DEFAULT_RECORDING_PREFIX = "recording"
DEFAULT_RECORDING_DIR = Path.home() / "Documents" / "WIIBBLE" / "recordings"
RECORDING_PREFIX_MAX_LEN = 40
RECORDING_TIMESTAMP_RE = re.compile(r"^(?P<prefix>.+)_(?P<timestamp>\d{12})$")

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

__all__ = [
    "DEFAULT_RECORDING_DIR",
    "DEFAULT_RECORDING_PREFIX",
    "RECORDING_PREFIX_MAX_LEN",
    "RECORDING_TIMESTAMP_RE",
    "build_features_filename",
    "build_recording_filename",
    "build_report_filename",
    "features_json_search_paths",
    "features_path_for",
    "normalize_recording_prefix",
    "parse_recording_stem",
    "report_path_for",
    "report_search_paths",
    "resolve_recording_dir",
    "recording_stem",
]


def resolve_recording_dir(out_dir: str = "") -> Path:
    """Return the directory used for CSV recordings."""
    if not out_dir:
        return DEFAULT_RECORDING_DIR
    return Path(out_dir)


def _escape_windows_reserved_name(prefix: str) -> str:
    """Avoid Windows reserved device names by suffixing ``_file``."""
    if prefix.upper() in _WINDOWS_RESERVED_NAMES:
        return f"{prefix}_file"
    return prefix


def normalize_recording_prefix(prefix: str) -> str:
    """Normalize a user-supplied recording filename prefix."""
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


def recording_stem(csv_path: Path | str) -> str:
    """Return the filename stem for a recording CSV."""
    return Path(csv_path).stem


def parse_recording_stem(stem: str) -> tuple[str, str] | None:
    """Split ``{prefix}_{YYMMDDHHMMSS}`` into prefix and timestamp, if matched."""
    match = RECORDING_TIMESTAMP_RE.match(stem)
    if not match:
        return None
    return match.group("prefix"), match.group("timestamp")


def build_features_filename(csv_path: Path | str) -> str:
    """Build the features JSON filename that mirrors the recording CSV stem."""
    return f"features_{recording_stem(csv_path)}.json"


def build_report_filename(csv_path: Path | str) -> str:
    """Build the HTML report filename that mirrors the recording CSV stem."""
    return f"report_{recording_stem(csv_path)}.html"


def features_path_for(csv_path: Path | str) -> Path:
    """Return the canonical features JSON path for a recording CSV."""
    csv = Path(csv_path)
    return csv.with_name(build_features_filename(csv))


def report_path_for(csv_path: Path | str) -> Path:
    """Return the canonical HTML report path for a recording CSV."""
    csv = Path(csv_path)
    return csv.with_name(build_report_filename(csv))


def _append_unique(paths: list[Path], candidate: Path) -> None:
    if candidate not in paths:
        paths.append(candidate)


def features_json_search_paths(csv_path: Path | str) -> list[Path]:
    """Return candidate features JSON paths, newest naming first."""
    csv = Path(csv_path)
    stem = csv.stem
    dirname = csv.parent
    candidates: list[Path] = [features_path_for(csv)]

    parsed = parse_recording_stem(stem)
    if parsed and parsed[0] == DEFAULT_RECORDING_PREFIX:
        _append_unique(candidates, dirname / f"features_{parsed[1]}.json")

    match = re.search(r"(\d{12})$", stem)
    if match:
        _append_unique(candidates, dirname / f"features_{match.group(1)}.json")

    match = re.search(r"(\d{8}_\d{6})", stem)
    if match:
        _append_unique(candidates, dirname / f"features_{match.group(1)}.json")

    return candidates


def report_search_paths(csv_path: Path | str) -> list[Path]:
    """Return candidate HTML report paths, newest naming first."""
    csv = Path(csv_path)
    stem = csv.stem
    dirname = csv.parent
    candidates: list[Path] = [report_path_for(csv)]

    parsed = parse_recording_stem(stem)
    if parsed and parsed[0] == DEFAULT_RECORDING_PREFIX:
        _append_unique(candidates, dirname / f"report_{parsed[1]}.html")

    match = re.search(r"(\d{12})$", stem)
    if match:
        _append_unique(candidates, dirname / f"report_{match.group(1)}.html")

    match = re.search(r"(\d{8}_\d{6})", stem)
    if match:
        _append_unique(candidates, dirname / f"report_{match.group(1)}.html")

    return candidates
