"""Shared helpers for CLI tools that scan the configured recordings folder."""

from __future__ import annotations

from pathlib import Path

from wiibble.board.recording import resolve_recording_dir
from wiibble.utils.state import Settings


def get_recordings_dir() -> Path:
    """Return the configured recordings directory from WIIBBLE settings."""
    return resolve_recording_dir(Settings.load().recording_dir)


def collect_recording_csvs() -> list[Path]:
    """Return sorted recording CSV paths in the configured recordings directory."""
    recordings_dir = get_recordings_dir()
    if not recordings_dir.is_dir():
        return []
    return sorted(recordings_dir.glob("*.csv"))
