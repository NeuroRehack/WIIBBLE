"""Tests for persisted tare offset helpers."""

from datetime import UTC, datetime
from unittest.mock import patch

from wiibble.ui.ui import _format_tare_status, _relative_tare_label
from wiibble.utils.state import Settings, default_data_struct


def test_default_data_struct_has_zero_tare():
    data_struct = default_data_struct()

    assert data_struct["top_right"]["tare"] == 0.0
    assert data_struct["bottom_right"]["rawIndex"] == 5


def test_save_and_apply_round_trip():
    settings = Settings()
    data_struct = default_data_struct()
    data_struct["top_right"]["tare"] = 30.5
    data_struct["bottom_right"]["tare"] = 31.0
    data_struct["top_left"]["tare"] = 29.5
    data_struct["bottom_left"]["tare"] = 30.0

    settings.tare_top_right = 30.5
    settings.tare_bottom_right = 31.0
    settings.tare_top_left = 29.5
    settings.tare_bottom_left = 30.0
    settings.tare_saved_at = "2026-07-27T12:00:00+00:00"

    fresh = default_data_struct()
    settings.apply_tare_to_data_struct(fresh)

    assert fresh["top_right"]["tare"] == 30.5
    assert fresh["bottom_left"]["tare"] == 30.0


def test_relative_tare_label_just_now():
    saved = datetime(2026, 7, 28, 12, 0, 0, tzinfo=UTC)
    now = saved.replace(second=30)

    assert _relative_tare_label(saved, now=now) == "just now"


def test_relative_tare_label_minutes():
    saved = datetime(2026, 7, 28, 12, 0, 0, tzinfo=UTC)
    now = saved.replace(minute=5)

    assert _relative_tare_label(saved, now=now) == "5 min ago"


def test_relative_tare_label_hours():
    saved = datetime(2026, 7, 28, 10, 0, 0, tzinfo=UTC)
    now = saved.replace(hour=13)

    assert _relative_tare_label(saved, now=now) == "3 hr ago"


def test_relative_tare_label_fallback_date():
    saved = datetime(2026, 7, 26, 10, 0, 0, tzinfo=UTC)
    now = datetime(2026, 7, 28, 10, 0, 0, tzinfo=UTC)

    label = _relative_tare_label(saved, now=now)

    assert label == saved.astimezone().strftime("%Y-%m-%d %H:%M")


def test_format_tare_status_uses_relative_label():
    settings = Settings(tare_saved_at="2026-07-28T10:00:00+00:00")

    with patch(
        "wiibble.ui.settings_panel._relative_tare_label", return_value="2 min ago"
    ):
        assert _format_tare_status(settings) == "Tare saved: 2 min ago"
