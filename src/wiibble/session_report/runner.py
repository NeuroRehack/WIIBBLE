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

log = logging.getLogger(__name__)


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
    features_path: str | None = None

    if duration_s >= MIN_ANALYSIS_DURATION_S:
        log.info(
            "Analysing %s (%.1f s) before report generation",
            csv_file.name,
            duration_s,
        )
        features = analyse_recording(str(csv_file))
        json_path = json_path_for(csv_file)
        json_path.write_text(
            json.dumps(features, indent=2, default=str), encoding="utf-8"
        )
        features_path = str(json_path)
        log.info("Features JSON written: %s", json_path.name)
    else:
        log.info(
            "Skipping analysis for %s (%.1f s < %.0f s minimum); report charts only",
            csv_file.name,
            duration_s,
            MIN_ANALYSIS_DURATION_S,
        )

    report_path = Path(
        generate_report(
            str(csv_file),
            features_path=features_path,
            out_path=str(out_path) if out_path is not None else None,
        )
    )

    if open_browser:
        open_report_in_browser(report_path)

    return report_path
