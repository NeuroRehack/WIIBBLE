# tests/test_ui.py
from wiibble.ui.theme import ICON_INFINITY
from wiibble.ui.ui import _format_record_limit, dashed_line_segments, sync_recording_buttons


class TestDashedLineSegments:
    def test_zero_length_returns_empty(self):
        assert dashed_line_segments((5, 5), (5, 5)) == []

    def test_horizontal_line_segments(self):
        segments = dashed_line_segments((0, 0), (30, 0), dash=8, gap=6)
        assert len(segments) == 3
        assert segments[0] == ((0, 0), (8, 0))
        assert segments[1] == ((14, 0), (22, 0))
        assert segments[2] == ((28, 0), (30, 0))

    def test_vertical_line_endpoints(self):
        segments = dashed_line_segments((10, 0), (10, 20), dash=10, gap=5)
        assert segments[0][0] == (10, 0)
        assert segments[-1][1] == (10, 20)


class TestFormatRecordLimit:
    def test_indefinite(self):
        assert _format_record_limit(0) == ICON_INFINITY

    def test_seconds(self):
        assert _format_record_limit(10) == "00:10"

    def test_minutes(self):
        assert _format_record_limit(90) == "01:30"


class TestSyncRecordingButtons:
    def test_sync_recording_buttons_idle(self, monkeypatch):
        labels = {}
        themes = {}
        idle_theme = object()

        def fake_exists(tag):
            return tag in ("start_recording_btn", "recording_quick_btn")

        def fake_set_label(tag, label):
            labels[tag] = label

        def fake_bind_theme(tag, theme):
            themes[tag] = theme

        import wiibble.ui.ui as ui_module

        monkeypatch.setattr(ui_module.dpg, "does_item_exist", fake_exists)
        monkeypatch.setattr(ui_module.dpg, "set_item_label", fake_set_label)
        monkeypatch.setattr(ui_module.dpg, "bind_item_theme", fake_bind_theme)
        monkeypatch.setattr(ui_module, "_get_recording_quick_idle_theme", lambda: idle_theme)

        sync_recording_buttons(recording_active=False)

        assert labels["start_recording_btn"] == "Start Recording"
        assert labels["recording_quick_btn"] == ""
        assert themes["start_recording_btn"] == 0
        assert themes["recording_quick_btn"] is idle_theme

    def test_sync_recording_buttons_active(self, monkeypatch):
        labels = {}
        themes = {}
        recording_theme = object()
        active_theme = object()

        def fake_exists(tag):
            return tag in ("start_recording_btn", "recording_quick_btn")

        def fake_set_label(tag, label):
            labels[tag] = label

        def fake_bind_theme(tag, theme):
            themes[tag] = theme

        import wiibble.ui.ui as ui_module

        monkeypatch.setattr(ui_module.dpg, "does_item_exist", fake_exists)
        monkeypatch.setattr(ui_module.dpg, "set_item_label", fake_set_label)
        monkeypatch.setattr(ui_module.dpg, "bind_item_theme", fake_bind_theme)
        monkeypatch.setattr(ui_module, "_get_recording_theme", lambda: recording_theme)
        monkeypatch.setattr(ui_module, "_get_recording_quick_active_theme", lambda: active_theme)

        sync_recording_buttons(recording_active=True)

        assert labels["start_recording_btn"] == "Stop Recording"
        assert labels["recording_quick_btn"] == ""
        assert themes["start_recording_btn"] is recording_theme
        assert themes["recording_quick_btn"] is active_theme
