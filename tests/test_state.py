# tests/test_state.py
# Unit tests for Settings persistence and AppState reset behaviour.

import json
import os

import pytest

from wiibble.utils.state import AppState, Settings


# Automatically set WIIBBLE_SETTINGS_PATH to a temp file for all tests in this module
@pytest.fixture(autouse=True)
def set_settings_path_env(tmp_path, monkeypatch):
    settings_file = os.path.join(tmp_path, ".wiibble", "settings.json")
    # Always create the parent directory for the settings file
    os.makedirs(os.path.dirname(settings_file), exist_ok=True)
    monkeypatch.setenv("WIIBBLE_SETTINGS_PATH", settings_file)


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
        assert Settings().record_duration == 30

    def test_cursor_size_default(self):
        assert Settings().cursor_size == 20

    def test_body_weight_kg_default(self):
        assert Settings().body_weight_kg == 70.0

    def test_scale_factor_default(self):
        from wiibble.utils.constants import SCALE_FACTOR_DEFAULT

        assert Settings().scale_factor == SCALE_FACTOR_DEFAULT

    def test_board_cal_reference_kg_default(self):
        assert Settings().board_cal_reference_kg == 20.0

    def test_flip_horizontal_default(self):
        assert Settings().flip_horizontal is False

    def test_flip_vertical_default(self):
        assert Settings().flip_vertical is False

    def test_recording_prefix_default(self):
        assert Settings().recording_prefix == ""

    def test_target_dwell_seconds_default(self):
        from wiibble.utils.constants import TARGET_DWELL_DEFAULT

        assert Settings().target_dwell_seconds == TARGET_DWELL_DEFAULT

    def test_show_target_counter_default(self):
        assert Settings().show_target_counter is True

    def test_thrive_defaults(self):
        s = Settings()
        assert s.thrive_enabled is False
        assert s.thrive_broker_host == "localhost"
        assert s.thrive_hub_id == "demo"
        assert s.thrive_node_id == "wiibble_01"


# ---------------------------------------------------------------------------
# Settings — load with no file
# ---------------------------------------------------------------------------


class TestSettingsLoadNoFile:
    def test_load_with_no_file_returns_defaults(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        s = Settings.load()
        assert s.trail_length == 100
        assert s.zoom_factor == 1.0
        assert s.cursor_size == 20

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
            cursor_size=25,
            body_weight_kg=82.5,
            scale_factor=2.8,
            board_cal_reference_kg=25.0,
            flip_horizontal=True,
            flip_vertical=True,
            recording_prefix="SPI001_SitStand",
            show_global_axes=False,
            show_local_axes=True,
            target_dwell_seconds=2,
            show_target_counter=False,
            auto_report_after_recording=False,
            open_report_in_browser=False,
        )
        original.save()
        loaded = Settings.load()

        assert loaded.trail_length == 50
        assert loaded.zoom_factor == 2.5
        assert loaded.filter_window == 10
        assert loaded.record_duration == 30
        assert loaded.cursor_size == 25
        assert loaded.body_weight_kg == 82.5
        assert loaded.scale_factor == 2.8
        assert loaded.board_cal_reference_kg == 25.0
        assert loaded.flip_horizontal is True
        assert loaded.flip_vertical is True
        assert loaded.recording_prefix == "SPI001_SitStand"
        assert loaded.show_global_axes is False
        assert loaded.show_local_axes is True
        assert loaded.target_dwell_seconds == 2
        assert loaded.show_target_counter is False
        assert loaded.auto_report_after_recording is False
        assert loaded.open_report_in_browser is False

    def test_report_settings_defaults(self):
        settings = Settings()
        assert settings.auto_report_after_recording is True
        assert settings.open_report_in_browser is True

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


class TestSettingsRecordingPrefix:
    def test_load_normalizes_invalid_prefix(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        path = env_settings_path()
        with open(path, "w") as f:
            json.dump({"recording_prefix": "SPI001/Sit Stand!!!"}, f)
        loaded = Settings.load()
        assert loaded.recording_prefix == "SPI001Sit_Stand"

    def test_load_persists_normalized_prefix(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        path = env_settings_path()
        with open(path, "w") as f:
            json.dump({"recording_prefix": " bad prefix "}, f)
        Settings.load()
        with open(path) as f:
            data = json.load(f)
        assert data["recording_prefix"] == "bad_prefix"

    def test_load_normalizes_windows_reserved_prefix(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        path = env_settings_path()
        with open(path, "w") as f:
            json.dump({"recording_prefix": "CON"}, f)
        loaded = Settings.load()
        assert loaded.recording_prefix == "CON_file"


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
        assert loaded.cursor_size == 20
        assert loaded.body_weight_kg == 70.0
        from wiibble.utils.constants import SCALE_FACTOR_DEFAULT

        assert loaded.scale_factor == SCALE_FACTOR_DEFAULT
        assert loaded.board_cal_reference_kg == 20.0

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
# Settings — tare persistence
# ---------------------------------------------------------------------------


class TestSettingsTarePersistence:
    def test_has_saved_tare_false_by_default(self):
        assert Settings().has_saved_tare() is False

    def test_tare_fields_survive_round_trip(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        original = Settings(
            tare_top_right=42.1,
            tare_bottom_right=41.8,
            tare_top_left=43.0,
            tare_bottom_left=42.5,
            tare_saved_at="2026-07-27T10:30:00+00:00",
        )
        original.save()
        loaded = Settings.load()

        assert loaded.tare_top_right == 42.1
        assert loaded.tare_bottom_right == 41.8
        assert loaded.tare_top_left == 43.0
        assert loaded.tare_bottom_left == 42.5
        assert loaded.tare_saved_at == "2026-07-27T10:30:00+00:00"
        assert loaded.has_saved_tare() is True

    def test_apply_tare_to_data_struct(self):
        settings = Settings(
            tare_top_right=10.0,
            tare_bottom_right=11.0,
            tare_top_left=12.0,
            tare_bottom_left=13.0,
            tare_saved_at="2026-07-27T10:30:00+00:00",
        )
        data_struct = {
            "top_right": {"rawIndex": 3, "tare": 0},
            "bottom_right": {"rawIndex": 5, "tare": 0},
            "top_left": {"rawIndex": 7, "tare": 0},
            "bottom_left": {"rawIndex": 9, "tare": 0},
        }

        settings.apply_tare_to_data_struct(data_struct)

        assert data_struct["top_right"]["tare"] == 10.0
        assert data_struct["bottom_right"]["tare"] == 11.0
        assert data_struct["top_left"]["tare"] == 12.0
        assert data_struct["bottom_left"]["tare"] == 13.0

    def test_save_tare_from_data_struct(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        settings = Settings()
        data_struct = {
            "top_right": {"rawIndex": 3, "tare": 20.0},
            "bottom_right": {"rawIndex": 5, "tare": 21.0},
            "top_left": {"rawIndex": 7, "tare": 22.0},
            "bottom_left": {"rawIndex": 9, "tare": 23.0},
        }

        settings.save_tare_from_data_struct(data_struct)
        loaded = Settings.load()

        assert loaded.tare_top_right == 20.0
        assert loaded.tare_bottom_right == 21.0
        assert loaded.tare_top_left == 22.0
        assert loaded.tare_bottom_left == 23.0
        assert loaded.has_saved_tare() is True
        assert loaded.tare_saved_at


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

    def test_reset_clears_target_hit_counter(self):
        s = AppState()
        s.target_hit_count = 5
        s._target_dwell_disarmed = {0}
        s.reset()
        assert s.target_hit_count == 0
        assert s._target_dwell_disarmed == set()

    def test_reset_preserves_saved_tare_from_settings(self):
        settings = Settings(
            tare_top_right=10.0,
            tare_bottom_right=11.0,
            tare_top_left=12.0,
            tare_bottom_left=13.0,
            tare_saved_at="2026-07-27T10:30:00+00:00",
        )
        app_state = AppState()
        app_state.data_struct["top_right"]["tare"] = 99.0

        app_state.reset(settings)

        assert app_state.data_struct["top_right"]["tare"] == 10.0
        assert app_state.data_struct["bottom_left"]["tare"] == 13.0

    def test_reset_zeros_tare_without_saved_settings(self):
        app_state = AppState()
        app_state.data_struct["top_right"]["tare"] = 42.0

        app_state.reset()

        assert app_state.data_struct["top_right"]["tare"] == 0.0


class TestAppStateResetSwayExtents:
    def test_reset_sway_extents_clears_trail_and_bbox(self):
        s = AppState()
        s.historical_coords = [(10, 20), (30, 40)]
        s.raw_max_x = 100.0
        s.raw_min_x = -50.0
        s.zoomed_max_y = 80.0
        s.zoomed_min_y = -20.0
        s.reset_sway_extents(30)
        assert s.historical_coords == [(0, 0)] * 30
        assert s.raw_max_x == s.raw_max_y == 0.0
        assert s.raw_min_x == s.raw_min_y == 0.0
        assert s.zoomed_max_x == s.zoomed_max_y == 0.0
        assert s.zoomed_min_x == s.zoomed_min_y == 0.0

    def test_reset_sway_extents_preserves_targets(self):
        s = AppState()
        s.clicked_locations = [{"center": (10, 20), "radius": 5}]
        s.reset_sway_extents(100)
        assert s.clicked_locations == [{"center": (10, 20), "radius": 5}]
