"""Tests for session_actions settings mutations."""

from wiibble.session_actions import (
    apply_body_weight,
    apply_recording_prefix,
    toggle_recording,
)
from wiibble.utils.state import AppState, Settings


def test_toggle_recording_starts_countdown():
    app_state = AppState(screen_width=800, screen_height=600)
    settings = Settings(record_duration=30)

    active = toggle_recording(app_state, settings)

    assert active is True
    assert app_state.is_countdown is True


def test_apply_body_weight_rejects_non_positive():
    app_state = AppState(screen_width=800, screen_height=600)
    settings = Settings(body_weight_kg=70.0)

    result = apply_body_weight(settings, app_state, 0)

    assert result is None
    assert settings.body_weight_kg == 70.0


def test_apply_recording_prefix_normalizes():
    settings = Settings()

    normalized = apply_recording_prefix(settings, "  SPI 001 ")

    assert normalized == "SPI_001"
    assert settings.recording_prefix == "SPI_001"
