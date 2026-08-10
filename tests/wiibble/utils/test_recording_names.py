"""Tests for recording filename normalization and sidecar naming."""

import datetime
from pathlib import Path

from wiibble.analysis.recording_meta import json_path_for
from wiibble.utils.recording_names import (
    build_features_filename,
    build_recording_filename,
    build_report_filename,
    features_json_search_paths,
    features_path_for,
    normalize_recording_prefix,
    parse_recording_stem,
    report_path_for,
    report_search_paths,
)


def test_normalize_strips_and_replaces_spaces():
    assert normalize_recording_prefix("  hello world ") == "hello_world"


def test_normalize_empty_returns_empty():
    assert normalize_recording_prefix("") == ""


def test_parse_recording_stem():
    assert parse_recording_stem("SPI001_SitStand_261101174543") == (
        "SPI001_SitStand",
        "261101174543",
    )
    assert parse_recording_stem("recording_261101174543") == (
        "recording",
        "261101174543",
    )
    assert parse_recording_stem("analysis_recording") is None


def test_sidecar_names_include_full_csv_stem():
    csv = "SPI001_SitStand_261101174543.csv"
    assert build_features_filename(csv) == "features_SPI001_SitStand_261101174543.json"
    assert build_report_filename(csv) == "report_SPI001_SitStand_261101174543.html"


def test_default_prefix_sidecars_include_recording_prefix():
    csv = "recording_261101174543.csv"
    assert build_features_filename(csv) == "features_recording_261101174543.json"
    assert build_report_filename(csv) == "report_recording_261101174543.html"
    assert json_path_for(Path(csv)).name == "features_recording_261101174543.json"


def test_build_recording_filename_matches_csv_convention():
    start = datetime.datetime(2026, 11, 1, 17, 45, 43)
    assert (
        build_recording_filename("SPI001_SitStand", start)
        == "SPI001_SitStand_261101174543.csv"
    )
    assert build_recording_filename("", start) == "recording_261101174543.csv"


def test_features_json_search_paths_prefers_canonical_then_legacy():
    csv = Path("recording_261101174543.csv")
    paths = [path.name for path in features_json_search_paths(csv)]
    assert paths[0] == "features_recording_261101174543.json"
    assert "features_261101174543.json" in paths


def test_report_search_paths_prefers_canonical_then_legacy():
    csv = Path("SPI001_SitStand_261101174543.csv")
    paths = [path.name for path in report_search_paths(csv)]
    assert paths[0] == "report_SPI001_SitStand_261101174543.html"
    assert "report_261101174543.html" in paths


def test_path_for_helpers():
    csv = Path("/tmp/SPI001_SitStand_261101174543.csv")
    assert features_path_for(csv).name == "features_SPI001_SitStand_261101174543.json"
    assert report_path_for(csv).name == "report_SPI001_SitStand_261101174543.html"
