"""Tests for session recording state transitions."""

from wiibble.session_recording import start_recording_countdown, stop_recording, toggle_recording
from wiibble.utils.state import AppState, Settings


def test_toggle_recording_starts_countdown():
    """First toggle arms the countdown and clears the buffer."""
    app_state = AppState(screen_width=800, screen_height=600)
    settings = Settings(record_duration=30)

    active = toggle_recording(app_state, settings)

    assert active is True
    assert app_state.is_countdown is True
    assert app_state.countdown_value == 4
    assert app_state.record_buffer == []


def test_toggle_recording_stops_active_session():
    """Second toggle stops recording or countdown."""
    app_state = AppState(screen_width=800, screen_height=600)
    settings = Settings()
    start_recording_countdown(app_state, settings)
    app_state.is_recording = True

    active = toggle_recording(app_state, settings)

    assert active is False
    assert app_state.is_recording is False
    assert app_state.is_countdown is False


def test_stop_recording_clears_flags():
    """stop_recording resets all recording-related runtime flags."""
    app_state = AppState(screen_width=800, screen_height=600)
    app_state.is_recording = True
    app_state.is_countdown = True
    app_state.recording_indicator = True

    stop_recording(app_state)

    assert app_state.is_recording is False
    assert app_state.is_countdown is False
    assert app_state.recording_indicator is False
