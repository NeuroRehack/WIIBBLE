"""Shared helpers for WIIBBLE recording CSV metadata (duration, sidecar paths)."""

from __future__ import annotations

from pathlib import Path

MIN_ANALYSIS_DURATION_S = 20.0


def json_path_for(csv_path: Path) -> Path:
    """Return the features JSON sidecar path for a recording CSV."""
    stem = csv_path.stem
    if stem.startswith("recording_"):
        return csv_path.with_name(stem.replace("recording_", "features_", 1) + ".json")
    return csv_path.with_name(f"features_{stem}.json")


def read_recording_duration_s(csv_path: Path) -> float:
    """Return recording duration in seconds without loading the whole file."""
    first_ts: float | None = None
    last_ts: float | None = None
    with csv_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(",")
            try:
                ts = float(parts[0])
            except ValueError:
                continue
            if first_ts is None:
                first_ts = ts
            last_ts = ts
    if first_ts is None or last_ts is None:
        return 0.0
    return last_ts - first_ts
