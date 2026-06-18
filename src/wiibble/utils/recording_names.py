"""Recording filename and path helpers (no I/O)."""

from __future__ import annotations

import re
from pathlib import Path

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

__all__ = [
    "DEFAULT_RECORDING_DIR",
    "DEFAULT_RECORDING_PREFIX",
    "RECORDING_PREFIX_MAX_LEN",
    "normalize_recording_prefix",
    "resolve_recording_dir",
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
