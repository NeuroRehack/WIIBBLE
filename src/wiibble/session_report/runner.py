"""Orchestrate analysis + HTML report for a single recording."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from wiibble.analysis.analysis import analyse_recording
from wiibble.analysis.recording_meta import (
    MIN_ANALYSIS_DURATION_S,
    json_path_for,
    read_recording_duration_s,
)
from wiibble.cli.report import generate_report
from wiibble.session_report.launcher import open_report_in_browser
from wiibble.session_report.progress import ReportProgressWriter, progress_path_for

log = logging.getLogger(__name__)

_ANALYSIS_STEPS = 5  # load, CoP, stabilogram, features, save JSON
_REPORT_BASE_STEPS = 2  # load CSV, build stabilogram
_FIGURE_STEPS = 6
_WRITE_HTML_STEP = 1


def _session_report_step_total(
    *,
    will_analyse: bool,
    will_include_feature_table: bool,
) -> int:
    """Return the total progress steps for a session report run."""
    analysis_steps = _ANALYSIS_STEPS if will_analyse else 0
    table_step = 1 if will_include_feature_table else 0
    report_steps = _REPORT_BASE_STEPS + _FIGURE_STEPS + table_step + _WRITE_HTML_STEP
    return analysis_steps + report_steps


def run_session_report(
    csv_path: str | Path,
    *,
    open_browser: bool = False,
    out_path: str | Path | None = None,
) -> Path:
    """Analyse (if long enough), generate HTML, optionally open in browser.

    Returns the path to the written HTML report.
    """
    csv_file = Path(csv_path).resolve()
    if not csv_file.is_file():
        raise FileNotFoundError(f"CSV not found: {csv_file}")

    duration_s = read_recording_duration_s(csv_file)
    will_analyse = duration_s >= MIN_ANALYSIS_DURATION_S
    features_json = json_path_for(csv_file)
    will_include_feature_table = will_analyse or features_json.is_file()

    progress = ReportProgressWriter(progress_path_for(csv_file))
    progress.configure(
        _session_report_step_total(
            will_analyse=will_analyse,
            will_include_feature_table=will_include_feature_table,
        ),
        "Starting...",
    )

    features_path: str | None = None
    try:
        if will_analyse:
            log.info(
                "Analysing %s (%.1f s) before report generation",
                csv_file.name,
                duration_s,
            )
            features = analyse_recording(str(csv_file), progress=progress)
            json_path = json_path_for(csv_file)
            progress.advance("Saving metrics...")
            json_path.write_text(
                json.dumps(features, indent=2, default=str), encoding="utf-8"
            )
            features_path = str(json_path)
            log.info("Features JSON written: %s", json_path.name)
        else:
            log.info(
                "Skipping analysis for %s (%.1f s < %.0f s minimum); "
                "report charts only",
                csv_file.name,
                duration_s,
                MIN_ANALYSIS_DURATION_S,
            )

        log.info("Generating HTML report for %s", csv_file.name)
        report_path = Path(
            generate_report(
                str(csv_file),
                features_path=features_path,
                out_path=str(out_path) if out_path is not None else None,
                progress=progress,
            )
        )
        log.info("Session report written: %s", report_path.name)

        if open_browser:
            open_report_in_browser(report_path)

        return report_path
    finally:
        progress.clear()
