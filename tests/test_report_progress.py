"""Tests for session-report progress sidecar I/O."""

from __future__ import annotations

import json
from unittest.mock import patch

from wiibble.session_report.progress import (
    ReportProgressWriter,
    progress_path_for,
    read_report_progress,
    remove_report_progress_file,
)


def test_progress_path_for_uses_recording_stem(tmp_path):
    csv_path = tmp_path / "SPI001_SitStand_261101174543.csv"
    assert progress_path_for(csv_path) == tmp_path / (
        "SPI001_SitStand_261101174543.report_progress.json"
    )


def test_writer_configure_advance_and_clear_round_trip(tmp_path):
    path = tmp_path / "recording.report_progress.json"
    writer = ReportProgressWriter(path)

    writer.configure(4, "Starting...")
    first = read_report_progress(path)
    assert first is not None
    assert first.label == "Starting..."
    assert first.step == 0
    assert first.total == 4
    assert first.pct == 0.0

    writer.advance("Loading recording...")
    second = read_report_progress(path)
    assert second is not None
    assert second.label == "Loading recording..."
    assert second.step == 1
    assert second.total == 4
    assert second.pct == 0.25

    writer.clear()
    assert not path.is_file()
    assert read_report_progress(path) is None


def test_writer_uses_atomic_replace(tmp_path):
    path = tmp_path / "recording.report_progress.json"
    writer = ReportProgressWriter(path)
    writer.configure(10, "Starting...")

    for index in range(10):
        writer.advance(f"Step {index + 1}")

    snapshot = read_report_progress(path)
    assert snapshot is not None
    assert snapshot.step == 10
    assert snapshot.total == 10
    assert snapshot.pct == 1.0
    assert not path.with_suffix(path.suffix + ".tmp").exists()


def test_read_report_progress_rejects_invalid_json(tmp_path):
    path = tmp_path / "bad.report_progress.json"
    path.write_text("{not json", encoding="utf-8")
    assert read_report_progress(path) is None


def test_read_report_progress_parses_written_payload(tmp_path):
    path = tmp_path / "recording.report_progress.json"
    path.write_text(
        json.dumps(
            {
                "label": "Computing features...",
                "step": 4,
                "total": 12,
                "pct": 0.33,
            }
        ),
        encoding="utf-8",
    )
    snapshot = read_report_progress(path)
    assert snapshot is not None
    assert snapshot.label == "Computing features..."
    assert snapshot.step == 4
    assert snapshot.total == 12
    assert snapshot.pct == 0.33


def test_remove_report_progress_file_is_best_effort(tmp_path):
    path = tmp_path / "recording.report_progress.json"
    path.write_text("{}", encoding="utf-8")
    remove_report_progress_file(path)
    assert not path.is_file()


def test_writer_write_failure_does_not_raise(tmp_path):
    path = tmp_path / "recording.report_progress.json"
    writer = ReportProgressWriter(path)
    with patch(
        "wiibble.session_report.progress._atomic_write_text",
        side_effect=OSError("locked"),
    ):
        writer.configure(3, "Starting...")
        writer.advance("Step 1")


def test_read_report_progress_retries_partial_json(tmp_path, monkeypatch):
    path = tmp_path / "recording.report_progress.json"
    path.write_text('{"label": "partial"', encoding="utf-8")
    sleeps: list[float] = []
    monkeypatch.setattr(
        "wiibble.session_report.progress.time.sleep",
        lambda delay: sleeps.append(delay),
    )
    assert read_report_progress(path) is None
    assert sleeps == [0.02]
