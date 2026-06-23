"""Regression tests for the offline posturographic analysis pipeline."""

from __future__ import annotations

import json
import math
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from wiibble.analysis.analysis import analyse_recording
from wiibble.cli.process_recordings import app as process_app

FIXTURES = Path(__file__).parent / "fixtures"
RECORDING_CSV = FIXTURES / "analysis_recording.csv"
GOLDEN_JSON = FIXTURES / "analysis_recording_features.json"

runner = CliRunner()

pytestmark = pytest.mark.analysis


def _values_equal(golden, actual) -> bool:
    if isinstance(golden, float) and isinstance(actual, float):
        if math.isnan(golden) and math.isnan(actual):
            return True
        return math.isclose(golden, actual, rel_tol=1e-9, abs_tol=1e-12)
    return golden == actual


def _assert_matches_golden(golden: dict, actual: dict) -> None:
    all_keys = sorted(set(golden) | set(actual))
    for key in all_keys:
        if key not in golden:
            pytest.fail(f"Unexpected key in output: {key!r} = {actual[key]!r}")
        if key not in actual:
            pytest.fail(f"Missing key in output: {key!r} (golden={golden[key]!r})")
        if not _values_equal(golden[key], actual[key]):
            pytest.fail(
                f"Mismatch for {key!r}: golden={golden[key]!r}, actual={actual[key]!r}"
            )


def test_analyse_recording_matches_golden():
    """Full pipeline output must match the pre-patch golden features JSON."""
    golden = json.loads(GOLDEN_JSON.read_text(encoding="utf-8"))
    actual = analyse_recording(str(RECORDING_CSV))
    _assert_matches_golden(golden, actual)


def test_process_recordings_writes_features(tmp_path):
    """CLI writes a features JSON whose values match the golden fixture."""
    csv_path = tmp_path / "analysis_recording.csv"
    shutil.copy(RECORDING_CSV, csv_path)

    result = runner.invoke(process_app, ["--no-report", str(csv_path)])
    assert result.exit_code == 0, result.output

    json_files = list(tmp_path.glob("features_*.json"))
    assert len(json_files) == 1

    golden = json.loads(GOLDEN_JSON.read_text(encoding="utf-8"))
    actual = json.loads(json_files[0].read_text(encoding="utf-8"))
    _assert_matches_golden(golden, actual)
