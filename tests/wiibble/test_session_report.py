"""Tests for end-of-session report orchestration."""

from __future__ import annotations

import json
import shutil
from unittest.mock import MagicMock, patch

import pytest

from tests.wiibble.test_analysis import (
    GOLDEN_JSON,
    RECORDING_CSV,
    _assert_matches_golden,
)
from wiibble.analysis.recording_meta import json_path_for
from wiibble.session_report.launcher import (
    parse_session_report_stdout,
    resolve_session_report_command,
)
from wiibble.session_report.progress import ReportProgressWriter, read_report_progress
from wiibble.session_report.runner import run_session_report

pytestmark = pytest.mark.analysis


def test_parse_session_report_stdout_ignores_log_lines():
    stdout = (
        "INFO wiibble.session_report.runner: Analysing recording.csv\n"
        "INFO wiibble.cli.report: Report written\n"
        "D:/recordings/report_SPI001_261101174543.html\n"
    )
    assert (
        parse_session_report_stdout(stdout)
        == "D:/recordings/report_SPI001_261101174543.html"
    )


def test_parse_session_report_stdout_single_line():
    assert parse_session_report_stdout("/tmp/report.html\n") == "/tmp/report.html"


def test_run_session_report_matches_golden(tmp_path):
    """Full session report writes features JSON and HTML for the fixture."""
    csv_path = tmp_path / "analysis_recording.csv"
    shutil.copy(RECORDING_CSV, csv_path)
    progress_path = csv_path.with_name(f"{csv_path.stem}.report_progress.json")

    report_path = run_session_report(csv_path, open_browser=False)

    assert report_path.is_file()
    assert report_path.suffix == ".html"
    assert not progress_path.is_file()

    features_path = json_path_for(csv_path)
    assert features_path.is_file()
    golden = json.loads(GOLDEN_JSON.read_text(encoding="utf-8"))
    actual = json.loads(features_path.read_text(encoding="utf-8"))
    _assert_matches_golden(golden, actual)


def test_run_session_report_writes_progress_steps_then_clears(tmp_path):
    """Progress sidecar advances monotonically and is removed on completion."""
    csv_path = tmp_path / "analysis_recording.csv"
    shutil.copy(RECORDING_CSV, csv_path)
    progress_path = csv_path.with_name(f"{csv_path.stem}.report_progress.json")

    seen_steps: list[int] = []

    original_advance = ReportProgressWriter.advance

    def tracking_advance(self, label: str) -> None:
        original_advance(self, label)
        snapshot = read_report_progress(self.path)
        if snapshot is not None:
            seen_steps.append(snapshot.step)

    with patch.object(ReportProgressWriter, "advance", tracking_advance):
        run_session_report(csv_path, open_browser=False)

    assert seen_steps
    assert seen_steps == sorted(seen_steps)
    assert seen_steps[-1] == seen_steps[0] + len(seen_steps) - 1
    assert not progress_path.is_file()


def test_run_session_report_short_recording_uses_fewer_steps(tmp_path):
    """Short recordings skip the metrics phase in the progress budget."""
    csv_path = tmp_path / "short_recording.csv"
    csv_path.write_text(
        "# total_weight_kg=70.0\n"
        "time (s),x (kg),y (kg)\n"
        + "\n".join(f"{i * 0.1:.1f},0.1,0.2" for i in range(150)),
        encoding="utf-8",
    )

    totals: list[int] = []
    original_configure = ReportProgressWriter.configure

    def capture_total(self, total: int, label: str = "Starting...") -> None:
        totals.append(total)
        original_configure(self, total, label)

    with patch.object(ReportProgressWriter, "configure", capture_total):
        run_session_report(csv_path, open_browser=False)

    assert totals == [9]


def test_run_session_report_skips_analysis_for_short_recording(tmp_path):
    """Recordings shorter than 20 s still get a chart-only HTML report."""
    csv_path = tmp_path / "short_recording.csv"
    csv_path.write_text(
        "# total_weight_kg=70.0\n"
        "time (s),x (kg),y (kg)\n"
        + "\n".join(f"{i * 0.1:.1f},0.1,0.2" for i in range(150)),
        encoding="utf-8",
    )

    report_path = run_session_report(csv_path, open_browser=False)

    assert report_path.is_file()
    assert not json_path_for(csv_path).exists()


def test_resolve_session_report_command_dev_mode():
    """Development builds invoke the Python module entrypoint."""
    with patch(
        "wiibble.session_report.launcher._is_standalone_app",
        return_value=False,
    ):
        command = resolve_session_report_command()
    assert command is not None
    assert command[-1] == "wiibble.cli.session_report"


def test_resolve_session_report_command_standalone_layout(tmp_path):
    """Installed builds use the companion exe in session_report/."""
    companion_dir = tmp_path / "session_report"
    companion_dir.mkdir()
    companion = companion_dir / "WIIBBLE-SessionReport.exe"
    companion.write_text("", encoding="utf-8")

    with (
        patch(
            "wiibble.session_report.launcher._is_standalone_app",
            return_value=True,
        ),
        patch(
            "wiibble.session_report.launcher.sys.executable",
            str(tmp_path / "WIIBBLE.exe"),
        ),
    ):
        command = resolve_session_report_command()

    assert command == [str(companion)]


def test_launch_session_report_puts_flags_before_csv_path():
    """Typer requires options before the CSV positional argument."""
    from wiibble.session_report.launcher import launch_session_report_async

    with (
        patch(
            "wiibble.session_report.launcher.resolve_session_report_command",
            return_value=["python", "-m", "wiibble.cli.session_report"],
        ),
        patch("wiibble.session_report.launcher.subprocess.Popen") as popen,
    ):
        launch_session_report_async("/tmp/recording.csv", open_browser=True)

    args = popen.call_args[0][0]
    assert args == [
        "python",
        "-m",
        "wiibble.cli.session_report",
        "--open",
        "/tmp/recording.csv",
    ]


def test_on_recording_saved_schedules_job():
    """Saving a recording launches the async session-report companion."""
    from wiibble.session import _on_recording_saved
    from wiibble.utils.state import AppState, Settings

    app_state = AppState()
    settings = Settings(auto_report_after_recording=True, open_report_in_browser=True)
    mock_process = MagicMock()

    with patch(
        "wiibble.session.launch_session_report_async",
        return_value=mock_process,
    ) as launch:
        _on_recording_saved("/tmp/recording_test.csv", app_state, settings)

    launch.assert_called_once_with(
        "/tmp/recording_test.csv",
        open_browser=True,
    )
    assert app_state.report_job is not None
    assert app_state.report_job["process"] is mock_process
    assert app_state.report_job["progress_path"].endswith(
        "recording_test.report_progress.json"
    )
    assert app_state.toast_message == "Recording saved"


def test_on_recording_saved_skips_when_disabled():
    """Auto-report can be turned off in settings."""
    from wiibble.session import _on_recording_saved
    from wiibble.utils.state import AppState, Settings

    app_state = AppState()
    settings = Settings(auto_report_after_recording=False)

    with patch("wiibble.session.launch_session_report_async") as launch:
        _on_recording_saved("/tmp/recording_test.csv", app_state, settings)

    launch.assert_not_called()
    assert app_state.report_job is None
    assert app_state.toast_message == "Recording saved"
