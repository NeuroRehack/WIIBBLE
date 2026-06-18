"""Recording state transitions for the main session loop."""

from __future__ import annotations

from wiibble.utils.state import AppState, Settings


def stop_recording(app_state: AppState) -> None:
    """Stop an active or pending recording session."""
    app_state.is_recording = False
    app_state.is_countdown = False
    app_state.recording_indicator = False
    app_state.stopwatch_elapsed = 0.0


def start_recording_countdown(app_state: AppState, settings: Settings) -> None:
    """Begin the pre-recording countdown and prepare the capture buffer."""
    app_state.is_countdown = True
    app_state.countdown_value = 4
    app_state.record_duration = settings.record_duration
    app_state.record_buffer = []
    app_state.recording_indicator = False
    app_state.stopwatch_elapsed = 0.0


def toggle_recording(app_state: AppState, settings: Settings) -> bool:
    """Toggle recording on or off.

    Returns:
        True when recording or countdown is now active, False when stopped.
    """
    if app_state.is_recording or app_state.is_countdown:
        stop_recording(app_state)
        return False
    start_recording_countdown(app_state, settings)
    return True
