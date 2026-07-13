"""Tests for session_actions settings mutations."""

from wiibble.session_actions import (
    apply_body_weight,
    apply_filter_window,
    apply_flip_vertical,
    apply_record_duration,
    apply_recording_dir,
    apply_recording_prefix,
    apply_setting_bool,
    apply_thrive_broker_host,
    apply_thrive_hub_id,
    apply_trail_length,
    apply_zoom_slider,
    request_calibrate_board,
    request_calibrate_scale,
    stop_recording,
    toggle_recording,
)
from wiibble.utils.state import AppState, Settings


def test_toggle_recording_starts_countdown():
    app_state = AppState(screen_width=800, screen_height=600)
    settings = Settings(record_duration=30)

    active = toggle_recording(app_state, settings)

    assert active is True
    assert app_state.is_countdown is True


def test_toggle_recording_stops_active_recording():
    app_state = AppState(screen_width=800, screen_height=600, is_recording=True)
    settings = Settings(record_duration=30)

    active = toggle_recording(app_state, settings, source="test")

    assert active is False
    assert app_state.is_recording is False
    assert app_state.is_countdown is False


def test_stop_recording_is_noop_when_idle():
    app_state = AppState(screen_width=800, screen_height=600)

    stop_recording(app_state, source="test")

    assert app_state.is_recording is False
    assert app_state.is_countdown is False


def test_apply_body_weight_rejects_non_positive():
    app_state = AppState(screen_width=800, screen_height=600)
    settings = Settings(body_weight_kg=70.0)

    result = apply_body_weight(settings, app_state, 0)

    assert result is None
    assert settings.body_weight_kg == 70.0


def test_apply_body_weight_updates_runtime_state():
    app_state = AppState(screen_width=800, screen_height=600)
    settings = Settings(body_weight_kg=70.0)

    result = apply_body_weight(settings, app_state, 72.5)

    assert result == 72.5
    assert settings.body_weight_kg == 72.5
    assert app_state.weight == 72.5


def test_apply_recording_prefix_normalizes():
    settings = Settings()

    normalized = apply_recording_prefix(settings, "  SPI 001 ")

    assert normalized == "SPI_001"
    assert settings.recording_prefix == "SPI_001"


def test_apply_record_duration_updates_runtime_state():
    app_state = AppState(screen_width=800, screen_height=600)
    settings = Settings(record_duration=30)

    result = apply_record_duration(settings, app_state, 60)

    assert result == 60
    assert settings.record_duration == 60
    assert app_state.record_duration == 60


def test_apply_trail_length_skips_unchanged_value():
    settings = Settings(trail_length=30)

    result = apply_trail_length(settings, 30)

    assert result == 30
    assert settings.trail_length == 30


def test_apply_filter_window_trims_buffer():
    app_state = AppState(screen_width=800, screen_height=600)
    app_state.filter_buffer = [1.0, 2.0, 3.0, 4.0, 5.0]
    settings = Settings(filter_window=1)

    apply_filter_window(settings, app_state, 2)

    assert settings.filter_window == 2
    assert app_state.filter_buffer == [4.0, 5.0]


def test_apply_setting_bool_updates_field():
    settings = Settings(show_bbox=False)

    apply_setting_bool(settings, "show_bbox", True)

    assert settings.show_bbox is True


def test_apply_flip_vertical_toggles():
    app_state = AppState(screen_width=800, screen_height=600)
    settings = Settings(flip_vertical=False)

    flipped = apply_flip_vertical(settings, app_state)

    assert flipped is True
    assert settings.flip_vertical is True


def test_apply_zoom_slider_updates_extents():
    app_state = AppState(
        screen_width=800,
        screen_height=600,
        raw_max_x=10.0,
        raw_max_y=20.0,
        raw_min_x=-10.0,
        raw_min_y=-20.0,
    )
    settings = Settings(zoom_factor=1.0)

    zoom = apply_zoom_slider(settings, app_state, 1.0)

    assert zoom > 1.0
    assert settings.zoom_factor == zoom
    assert app_state.zoomed_max_x == app_state.raw_max_x * zoom


def test_apply_recording_dir_persists_path():
    settings = Settings(recording_dir="")

    path = apply_recording_dir(settings, "D:/recordings")

    assert path == "D:/recordings"
    assert settings.recording_dir == "D:/recordings"


def test_request_calibrate_board_queues_action():
    session_state: dict = {}

    request_calibrate_board(session_state)

    assert session_state["action"] == "calibrate"


def test_request_calibrate_scale_queues_action():
    session_state: dict = {}

    request_calibrate_scale(session_state)

    assert session_state["action"] == "calibrate_scale"


def test_apply_thrive_broker_host_strips_and_sets():
    settings = Settings()

    host = apply_thrive_broker_host(settings, " 192.168.1.50 ")

    assert host == "192.168.1.50"
    assert settings.thrive_broker_host == "192.168.1.50"


def test_apply_thrive_hub_id_strips_and_sets():
    settings = Settings()

    hub = apply_thrive_hub_id(settings, " clinic_a ")

    assert hub == "clinic_a"
    assert settings.thrive_hub_id == "clinic_a"


def test_apply_thrive_enabled_bool():
    settings = Settings()

    apply_setting_bool(settings, "thrive_enabled", True)

    assert settings.thrive_enabled is True
