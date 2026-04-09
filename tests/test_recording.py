# tests/test_recording.py
# Unit tests for _save_recording_csv in recording.py.
# Uses tmp_path + monkeypatch.chdir so no files are written to the real workspace.
import csv
import os
import re

import pytest

from recording import _save_recording_csv


def _find_csv(recordings_dir) -> str:
    """Return the single CSV file in the recordings directory."""
    files = [f for f in os.listdir(recordings_dir) if f.endswith(".csv")]
    assert len(files) == 1, f"Expected 1 CSV file, found: {files}"
    return os.path.join(recordings_dir, files[0])


def _read_csv(path) -> list:
    with open(path, newline="") as f:
        return list(csv.reader(f))


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
        _save_recording_csv([])
        assert recordings_dir.is_dir()

    def test_recordings_dir_reused_if_already_exists(self, tmp_path):
        recordings_dir = tmp_path / "recordings"
        recordings_dir.mkdir()
        _save_recording_csv([])  # must not raise
        assert recordings_dir.is_dir()


# ---------------------------------------------------------------------------
# File naming
# ---------------------------------------------------------------------------


class TestFilenaming:
    def test_filename_matches_expected_pattern(self, tmp_path):
        _save_recording_csv([])
        recordings_dir = os.path.join(tmp_path, "recordings")
        files = os.listdir(recordings_dir)
        assert len(files) == 1
        assert re.fullmatch(r"recording_\d{8}_\d{6}\.csv", files[0])


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------


class TestHeader:
    def test_empty_buffer_writes_header_only(self, tmp_path):
        _save_recording_csv([])
        path = _find_csv(os.path.join(tmp_path, "recordings"))
        rows = _read_csv(path)
        assert len(rows) == 1
        assert rows[0] == ["time (s)", "x (kg)", "y (kg)"]

    def test_header_is_exactly_correct(self, tmp_path):
        _save_recording_csv([(0.0, 1.0, 2.0)])
        path = _find_csv(os.path.join(tmp_path, "recordings"))
        rows = _read_csv(path)
        assert rows[0] == ["time (s)", "x (kg)", "y (kg)"]


# ---------------------------------------------------------------------------
# Row content and formatting
# ---------------------------------------------------------------------------


class TestRowContent:
    def test_single_row_values_present(self, tmp_path):
        _save_recording_csv([(1.234, 5.678, -9.012)])
        path = _find_csv(os.path.join(tmp_path, "recordings"))
        rows = _read_csv(path)
        assert len(rows) == 2  # header + 1 data row
        assert rows[1] == ["1.234", "5.678", "-9.012"]

    def test_three_rows_all_written(self, tmp_path):
        buffer = [(0.0, 0.1, 0.2), (0.01, 0.11, 0.21), (0.02, 0.12, 0.22)]
        _save_recording_csv(buffer)
        path = _find_csv(os.path.join(tmp_path, "recordings"))
        rows = _read_csv(path)
        assert len(rows) == 4  # header + 3 data rows

    def test_values_formatted_to_three_decimal_places(self, tmp_path):
        _save_recording_csv([(0.01, 1.0, 2.0)])
        path = _find_csv(os.path.join(tmp_path, "recordings"))
        rows = _read_csv(path)
        # "0.010" not "0.01"
        assert rows[1][0] == "0.010"
        assert rows[1][1] == "1.000"
        assert rows[1][2] == "2.000"

    def test_negative_values_written_correctly(self, tmp_path):
        _save_recording_csv([(0.0, -1.5, -2.75)])
        path = _find_csv(os.path.join(tmp_path, "recordings"))
        rows = _read_csv(path)
        assert rows[1][1] == "-1.500"
        assert rows[1][2] == "-2.750"

    def test_row_order_preserved(self, tmp_path):
        buffer = [(float(i), float(i), float(i)) for i in range(5)]
        _save_recording_csv(buffer)
        path = _find_csv(os.path.join(tmp_path, "recordings"))
        rows = _read_csv(path)
        for idx, row in enumerate(rows[1:]):
            assert row[0] == f"{float(idx):.3f}"
