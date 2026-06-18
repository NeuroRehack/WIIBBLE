"""Tests for recording filename normalization."""

from wiibble.utils.recording_names import normalize_recording_prefix


def test_normalize_strips_and_replaces_spaces():
    assert normalize_recording_prefix("  hello world ") == "hello_world"


def test_normalize_empty_returns_empty():
    assert normalize_recording_prefix("") == ""
