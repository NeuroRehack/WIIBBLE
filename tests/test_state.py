# tests/test_state.py
# Unit tests for Settings persistence and AppState reset behaviour.

import json
import os

import pytest


# Automatically set WIIBBLE_SETTINGS_PATH to a temp file for all tests in this module
@pytest.fixture(autouse=True)
def set_settings_path_env(tmp_path, monkeypatch):
    settings_file = os.path.join(tmp_path, ".wiibble", "settings.json")
    # Always create the parent directory for the settings file
    os.makedirs(os.path.dirname(settings_file), exist_ok=True)
    monkeypatch.setenv("WIIBBLE_SETTINGS_PATH", settings_file)


from state import AppState, Settings

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def env_settings_path():
    return os.environ["WIIBBLE_SETTINGS_PATH"]


# ---------------------------------------------------------------------------
# Settings — defaults
# ---------------------------------------------------------------------------


class TestSettingsDefaults:
    def test_trail_length_default(self):
        assert Settings().trail_length == 100

    def test_zoom_factor_default(self):
        assert Settings().zoom_factor == 1.0

    def test_filter_window_default(self):
        assert Settings().filter_window == 1

    def test_record_duration_default(self):
        assert Settings().record_duration == 10

    def test_cursor_mode_default(self):
        assert Settings().cursor_mode == "avatar"


# ---------------------------------------------------------------------------
# Settings — load with no file
# ---------------------------------------------------------------------------


class TestSettingsLoadNoFile:
    def test_load_with_no_file_returns_defaults(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        s = Settings.load()
        assert s.trail_length == 100
        assert s.zoom_factor == 1.0
        assert s.cursor_mode == "avatar"

    def test_load_with_no_file_does_not_raise(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        Settings.load()  # must not raise


# ---------------------------------------------------------------------------
# Settings — save / load round-trip
# ---------------------------------------------------------------------------


class TestSettingsRoundTrip:
    def test_all_fields_survive_round_trip(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        original = Settings(
            trail_length=50,
            zoom_factor=2.5,
            filter_window=10,
            record_duration=30,
            cursor_mode="circle",
        )
        original.save()
        loaded = Settings.load()

        assert loaded.trail_length == 50
        assert loaded.zoom_factor == 2.5
        assert loaded.filter_window == 10
        assert loaded.record_duration == 30
        assert loaded.cursor_mode == "circle"

    def test_save_creates_directory_if_missing(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        Settings().save()
        assert os.path.isfile(env_settings_path())

    def test_save_writes_valid_json(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        Settings().save()
        with open(env_settings_path()) as f:
            data = json.load(f)
        assert "trail_length" in data
        assert "zoom_factor" in data


# ---------------------------------------------------------------------------
# Settings — load with partial / corrupt JSON
# ---------------------------------------------------------------------------


class TestSettingsLoadFallback:
    def test_partial_json_fills_missing_keys_with_defaults(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        path = env_settings_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        # Write only one field
        with open(path, "w") as f:
            json.dump({"trail_length": 25}, f)

        loaded = Settings.load()
        assert loaded.trail_length == 25
        # All other fields fall back to default
        assert loaded.zoom_factor == 1.0
        assert loaded.cursor_mode == "avatar"

    def test_corrupt_json_returns_defaults(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        path = env_settings_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write("{ not valid json }")

        loaded = Settings.load()
        assert loaded.trail_length == 100
        assert loaded.zoom_factor == 1.0

    def test_unknown_keys_in_json_are_ignored(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        path = env_settings_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump({"trail_length": 77, "unknown_future_key": "whatever"}, f)

        loaded = Settings.load()
        assert loaded.trail_length == 77
        assert not hasattr(loaded, "unknown_future_key")


# ---------------------------------------------------------------------------
# Settings — toggle_cursor_mode
# ---------------------------------------------------------------------------


class TestToggleCursorMode:
    def test_avatar_toggles_to_circle(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        s = Settings(cursor_mode="avatar")
        s.toggle_cursor_mode()
        assert s.cursor_mode == "circle"

    def test_circle_toggles_to_avatar(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        s = Settings(cursor_mode="circle")
        s.toggle_cursor_mode()
        assert s.cursor_mode == "avatar"

    def test_toggle_twice_returns_to_original(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        s = Settings(cursor_mode="avatar")
        s.toggle_cursor_mode()
        s.toggle_cursor_mode()
        assert s.cursor_mode == "avatar"


# ---------------------------------------------------------------------------
# AppState — reset
# ---------------------------------------------------------------------------


class TestAppStateReset:
    def test_reset_clears_ball_position(self):
        s = AppState(ball_x=99, ball_y=88)
        s.reset()
        assert s.ball_x == 0
        assert s.ball_y == 0

    def test_reset_clears_is_recording(self):
        s = AppState()
        s.is_recording = True
        s.reset()
        assert s.is_recording is False

    def test_reset_clears_record_buffer(self):
        s = AppState()
        s.record_buffer = [(0.1, 1.0, 2.0), (0.2, 1.1, 2.1)]
        s.reset()
        assert s.record_buffer == []

    def test_reset_clears_filter_buffer(self):
        s = AppState()
        s.filter_buffer = [{"top_right": 1.0}]
        s.reset()
        assert s.filter_buffer == []

    def test_reset_clears_clicked_locations(self):
        s = AppState()
        s.clicked_locations = [{"center": (10, 20), "radius": 5}]
        s.reset()
        assert s.clicked_locations == []

    def test_reset_preserves_weight(self):
        # weight is calibration result — must survive a session restart
        s = AppState(weight=72.5)
        s.reset()
        assert s.weight == 72.5

    def test_reset_clears_pan_offsets(self):
        s = AppState(pan_offset_x=50.0, pan_offset_y=-30.0)
        s.reset()
        assert s.pan_offset_x == 0.0
        assert s.pan_offset_y == 0.0
