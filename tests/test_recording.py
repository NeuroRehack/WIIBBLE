# tests/test_recording.py
# Unit tests for _save_recording_csv in recording.py.
# Uses tmp_path + monkeypatch.chdir so no files are written to the real workspace.
import csv
import datetime
import os
import re

import pytest

from wiibble.board.recording import (
    _save_recording_csv,
    build_recording_filename,
    normalize_recording_prefix,
)


def _find_csv(recordings_dir) -> str:
    """Return the single CSV file in the recordings directory."""
    files = [f for f in os.listdir(recordings_dir) if f.endswith(".csv")]
    assert len(files) == 1, f"Expected 1 CSV file, found: {files}"
    return os.path.join(recordings_dir, files[0])


def _read_csv(path) -> list:
    """Return CSV rows, skipping metadata comment lines (lines starting with #)."""
    with open(path, newline="") as f:
        return [row for row in csv.reader(f) if not (row and row[0].startswith("#"))]


def _read_metadata(path) -> dict:
    """Return metadata comment lines as key/value pairs."""
    metadata = {}
    with open(path) as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith("#"):
                content = stripped[1:].strip()
                key, _, val = content.partition("=")
                if val:
                    metadata[key.strip()] = val.strip()
    return metadata


@pytest.fixture(autouse=True)
def use_tmp_dir(tmp_path, monkeypatch):
    """All tests run with cwd set to a temp directory so recordings/ stays isolated."""
    monkeypatch.chdir(tmp_path)


# ---------------------------------------------------------------------------
# Directory creation
# ---------------------------------------------------------------------------


class TestDirectoryCreation:
    def test_recordings_dir_created_if_missing(self, tmp_path):
        recordings_dir = tmp_path / "recordings"
        assert not recordings_dir.exists()
        _save_recording_csv([], out_dir=str(recordings_dir))
        assert recordings_dir.is_dir()

    def test_recordings_dir_reused_if_already_exists(self, tmp_path):
        recordings_dir = tmp_path / "recordings"
        recordings_dir.mkdir()
        _save_recording_csv([], out_dir=str(recordings_dir))  # must not raise
        assert recordings_dir.is_dir()


# ---------------------------------------------------------------------------
# File naming
# ---------------------------------------------------------------------------


class TestFilenaming:
    def test_filename_matches_expected_pattern(self, tmp_path):
        recordings_dir = os.path.join(tmp_path, "recordings")
        _save_recording_csv([], out_dir=recordings_dir)
        files = os.listdir(recordings_dir)
        assert len(files) == 1
        assert re.fullmatch(r"recording_\d{12}\.csv", files[0])

    def test_blank_prefix_uses_default(self, tmp_path):
        recordings_dir = os.path.join(tmp_path, "recordings")
        start = datetime.datetime(2026, 11, 1, 17, 45, 43)
        _save_recording_csv([], out_dir=recordings_dir, prefix="", start_time=start)
        assert os.listdir(recordings_dir) == ["recording_261101174543.csv"]

    def test_custom_prefix(self, tmp_path):
        recordings_dir = os.path.join(tmp_path, "recordings")
        start = datetime.datetime(2026, 11, 1, 17, 45, 43)
        _save_recording_csv([], out_dir=recordings_dir, prefix="SPI001_SitStand", start_time=start)
        assert os.listdir(recordings_dir) == ["SPI001_SitStand_261101174543.csv"]

    def test_unsafe_prefix_chars_removed(self):
        start = datetime.datetime(2026, 11, 1, 17, 45, 43)
        filename = build_recording_filename("SPI001/Sit:Stand", start)
        assert filename == "SPI001SitStand_261101174543.csv"

    def test_spaces_replaced_with_underscores(self):
        start = datetime.datetime(2026, 11, 1, 17, 45, 43)
        assert (
            build_recording_filename("SPI001 SitStand", start) == "SPI001_SitStand_261101174543.csv"
        )

    def test_build_recording_filename_strips_whitespace(self):
        start = datetime.datetime(2026, 1, 2, 3, 4, 5)
        assert build_recording_filename("  myprefix  ", start) == "myprefix_260102030405.csv"

    def test_prefix_truncated_to_max_length(self):
        long_prefix = "A" * 50
        assert len(normalize_recording_prefix(long_prefix)) == 40

    def test_prefix_only_special_chars_falls_back_to_default(self):
        start = datetime.datetime(2026, 1, 2, 3, 4, 5)
        assert build_recording_filename("!!!", start) == "recording_260102030405.csv"

    def test_normalize_collapses_repeated_underscores(self):
        assert normalize_recording_prefix("SPI001  SitStand") == "SPI001_SitStand"

    def test_leading_dots_stripped(self):
        assert normalize_recording_prefix(".hidden") == "hidden"
        assert normalize_recording_prefix("...SPI001") == "SPI001"

    def test_windows_reserved_name_escaped(self):
        assert normalize_recording_prefix("CON") == "CON_file"
        assert normalize_recording_prefix("com1") == "com1_file"
        assert normalize_recording_prefix("LPT9") == "LPT9_file"

    def test_windows_reserved_name_in_filename(self):
        start = datetime.datetime(2026, 1, 2, 3, 4, 5)
        assert build_recording_filename("CON", start) == "CON_file_260102030405.csv"

    def test_collision_appends_numeric_suffix(self, tmp_path):
        recordings_dir = os.path.join(tmp_path, "recordings")
        start = datetime.datetime(2026, 11, 1, 17, 45, 43)
        kwargs = dict(out_dir=recordings_dir, prefix="SPI001", start_time=start)
        _save_recording_csv([], **kwargs)
        _save_recording_csv([], **kwargs)
        assert sorted(os.listdir(recordings_dir)) == [
            "SPI001_261101174543.csv",
            "SPI001_261101174543_2.csv",
        ]


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------


class TestHeader:
    def test_empty_buffer_writes_header_only(self, tmp_path):
        recordings_dir = os.path.join(tmp_path, "recordings")
        _save_recording_csv([], out_dir=recordings_dir)
        path = _find_csv(recordings_dir)
        rows = _read_csv(path)
        assert len(rows) == 1
        assert rows[0] == ["time (s)", "x (kg)", "y (kg)"]

    def test_header_is_exactly_correct(self, tmp_path):
        recordings_dir = os.path.join(tmp_path, "recordings")
        _save_recording_csv([(0.0, 1.0, 2.0)], out_dir=recordings_dir)
        path = _find_csv(recordings_dir)
        rows = _read_csv(path)
        assert rows[0] == ["time (s)", "x (kg)", "y (kg)"]


# ---------------------------------------------------------------------------
# Row content and formatting
# ---------------------------------------------------------------------------


class TestRowContent:
    def test_single_row_values_present(self, tmp_path):
        recordings_dir = os.path.join(tmp_path, "recordings")
        _save_recording_csv([(1.234, 5.678, -9.012)], out_dir=recordings_dir)
        path = _find_csv(recordings_dir)
        rows = _read_csv(path)
        assert len(rows) == 2  # header + 1 data row
        assert rows[1] == ["1.234", "5.678", "-9.012"]

    def test_three_rows_all_written(self, tmp_path):
        buffer = [(0.0, 0.1, 0.2), (0.01, 0.11, 0.21), (0.02, 0.12, 0.22)]
        recordings_dir = os.path.join(tmp_path, "recordings")
        _save_recording_csv(buffer, out_dir=recordings_dir)
        path = _find_csv(recordings_dir)
        rows = _read_csv(path)
        assert len(rows) == 4  # header + 3 data rows

    def test_values_formatted_to_three_decimal_places(self, tmp_path):
        recordings_dir = os.path.join(tmp_path, "recordings")
        _save_recording_csv([(0.01, 1.0, 2.0)], out_dir=recordings_dir)
        path = _find_csv(recordings_dir)
        rows = _read_csv(path)
        # "0.010" not "0.01"
        assert rows[1][0] == "0.010"
        assert rows[1][1] == "1.000"
        assert rows[1][2] == "2.000"

    def test_negative_values_written_correctly(self, tmp_path):
        recordings_dir = os.path.join(tmp_path, "recordings")
        _save_recording_csv([(0.0, -1.5, -2.75)], out_dir=recordings_dir)
        path = _find_csv(recordings_dir)
        rows = _read_csv(path)
        assert rows[1][1] == "-1.500"
        assert rows[1][2] == "-2.750"

    def test_row_order_preserved(self, tmp_path):
        buffer = [(float(i), float(i), float(i)) for i in range(5)]
        recordings_dir = os.path.join(tmp_path, "recordings")
        _save_recording_csv(buffer, out_dir=recordings_dir)
        path = _find_csv(recordings_dir)
        rows = _read_csv(path)
        for idx, row in enumerate(rows[1:]):
            assert row[0] == f"{float(idx):.3f}"


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


class TestMetadata:
    def test_flip_metadata_defaults_false(self, tmp_path):
        recordings_dir = os.path.join(tmp_path, "recordings")
        path = _save_recording_csv([], out_dir=recordings_dir)
        metadata = _read_metadata(path)
        assert metadata["flip_horizontal"] == "false"
        assert metadata["flip_vertical"] == "false"

    def test_flip_metadata_true_when_enabled(self, tmp_path):
        recordings_dir = os.path.join(tmp_path, "recordings")
        path = _save_recording_csv(
            [],
            out_dir=recordings_dir,
            flip_horizontal=True,
            flip_vertical=True,
        )
        metadata = _read_metadata(path)
        assert metadata["flip_horizontal"] == "true"
        assert metadata["flip_vertical"] == "true"
