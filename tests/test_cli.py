"""CLI argument parsing and exit codes for Typer entry points."""

from __future__ import annotations

from unittest.mock import patch

from typer.testing import CliRunner

from wiibble.cli.process_recordings import app as process_app
from wiibble.cli.report import app as report_app

runner = CliRunner()


def test_process_recordings_help():
    """Show help when invoked with no mode flags."""
    result = runner.invoke(process_app, [])
    assert result.exit_code == 0
    assert "Offline posturographic analysis" in result.output


def test_process_recordings_missing_file():
    """Exit with error when an explicit CSV path does not exist."""
    result = runner.invoke(process_app, ["missing.csv"])
    assert result.exit_code != 0


def test_process_recordings_new_empty_dir(tmp_path, monkeypatch):
    """--new reports when the recordings directory has no CSV files."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "recordings").mkdir()
    result = runner.invoke(process_app, ["--new"])
    assert result.exit_code == 0
    assert "No recording CSVs found" in result.output


def test_process_recordings_skips_short_recording(tmp_path, monkeypatch):
    """Recordings shorter than the minimum duration are skipped."""
    monkeypatch.chdir(tmp_path)
    rec_dir = tmp_path / "recordings"
    rec_dir.mkdir()
    csv_path = rec_dir / "recording_test.csv"
    csv_path.write_text("# total_weight_kg=70.0\n0.0,0.1,0.2\n1.0,0.1,0.2\n", encoding="utf-8")

    result = runner.invoke(process_app, [str(csv_path)])
    assert result.exit_code == 0
    assert "[skip]" in result.output


def test_report_help():
    """Report CLI requires a CSV argument."""
    result = runner.invoke(report_app, ["--help"])
    assert result.exit_code == 0
    assert "posturographic HTML report" in result.output


def test_report_missing_csv():
    """Report CLI fails when the CSV path does not exist."""
    result = runner.invoke(report_app, ["missing.csv"])
    assert result.exit_code != 0


def test_report_success(tmp_path):
    """Generate a report for a minimal valid recording CSV."""
    csv_path = tmp_path / "recording_20260101_120000.csv"
    csv_path.write_text(
        "# total_weight_kg=70.0\n"
        "time (s),x (kg),y (kg)\n" + "\n".join(f"{i:.1f},0.1,0.2" for i in range(300)),
        encoding="utf-8",
    )

    with patch("wiibble.cli.report.generate_report", return_value=str(tmp_path / "out.html")):
        result = runner.invoke(report_app, [str(csv_path)])

    assert result.exit_code == 0
    assert "Report saved to:" in result.output
