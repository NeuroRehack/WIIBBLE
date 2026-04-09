import math

import input as input_module
from state import AppState


class DummySettings:
    def __init__(self, cursor_mode="avatar", zoom_factor=1.0):
        self.cursor_mode = cursor_mode
        self.zoom_factor = zoom_factor
        self.toggled = False

    def toggle_cursor_mode(self):
        self.toggled = True
        self.cursor_mode = "circle" if self.cursor_mode == "avatar" else "avatar"


class DummyRegistry:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_handle_canvas_click_toggles_cursor_when_ball_hit(monkeypatch):
    app_state = AppState(screen_width=200, screen_height=100, ball_x=100, ball_y=50)
    settings = DummySettings(cursor_mode="avatar")
    session_state = {"toolbar_visible": False}
    monkeypatch.setattr(input_module.dpg, "is_key_down", lambda _key: False)

    input_module._handle_canvas_click(100, 50, app_state, settings, session_state)

    assert settings.cursor_mode == "circle"
    assert settings.toggled is True
    assert app_state.target_in_progress is None


def test_handle_canvas_click_starts_target_when_click_off_cursor(monkeypatch):
    app_state = AppState(screen_width=200, screen_height=100, ball_x=0, ball_y=0)
    settings = DummySettings(cursor_mode="circle", zoom_factor=1.0)
    session_state = {"toolbar_visible": False}
    monkeypatch.setattr(input_module.dpg, "is_key_down", lambda _key: False)

    input_module._handle_canvas_click(150, 75, app_state, settings, session_state)

    assert app_state.target_in_progress is not None
    assert app_state.target_in_progress["center"] == (50.0, 25.0)
    assert app_state.target_in_progress["radius"] == 5.0


def test_handle_target_drag_updates_target_radius(monkeypatch):
    app_state = AppState(screen_width=200, screen_height=100)
    app_state.target_in_progress = {"center": (0.0, 0.0), "radius": 5.0}
    settings = DummySettings(zoom_factor=1.0)
    monkeypatch.setattr(input_module.dpg, "get_mouse_pos", lambda local=False: (110, 50))

    input_module._handle_target_drag(app_state, settings)

    assert math.isclose(app_state.target_in_progress["radius"], 10.0, rel_tol=1e-6)


def test_handle_target_release_appends_target():
    app_state = AppState()
    app_state.target_in_progress = {"center": (4.0, 2.0), "radius": 5.0}

    input_module._handle_target_release(app_state)

    assert app_state.target_in_progress is None
    assert app_state.clicked_locations == [{"center": (4.0, 2.0), "radius": 5.0}]


def test_handle_pan_drag_starts_and_moves(monkeypatch):
    app_state = AppState(screen_width=200, screen_height=100, pan_offset_x=0.0, pan_offset_y=0.0)
    session_state = {}
    monkeypatch.setattr(input_module.dpg, "is_key_down", lambda _key: True)
    monkeypatch.setattr(input_module.dpg, "get_mouse_pos", lambda local=False: (50, 50))

    input_module._handle_pan_drag(app_state, session_state)

    assert app_state.is_panning is True
    assert app_state.pan_start_mouse == (50, 50)
    assert app_state.pan_start_offset == (0.0, 0.0)

    monkeypatch.setattr(input_module.dpg, "get_mouse_pos", lambda local=False: (60, 55))
    input_module._handle_pan_drag(app_state, session_state)

    assert app_state.pan_offset_x == 10.0
    assert app_state.pan_offset_y == 5.0
    assert session_state["action"] == "pan_changed"


def test_handle_pan_release_resets_panning():
    app_state = AppState()
    app_state.is_panning = True

    input_module._handle_pan_release(app_state)

    assert app_state.is_panning is False


def test_handle_mouse_wheel_performs_pan_and_zooms(monkeypatch):
    app_state = AppState(screen_width=200, screen_height=100, pan_offset_x=0.0, pan_offset_y=0.0)
    settings = DummySettings(zoom_factor=1.0)
    session_state = {}
    recorded = {"value": None, "zoom_called": False}

    monkeypatch.setattr(input_module.dpg, "is_key_down", lambda _key: True)
    monkeypatch.setattr(input_module.dpg, "get_mouse_pos", lambda local=False: (120, 60))
    monkeypatch.setattr(input_module.dpg, "set_value", lambda tag, value: recorded.update({"value": value}))
    monkeypatch.setattr(input_module, "_on_zoom_change", lambda slider_value, settings_, app_state_: recorded.update({"zoom_called": True}))

    input_module._handle_mouse_wheel(1.0, app_state, session_state, settings)

    assert session_state["action"] == "pan_changed"
    assert recorded["zoom_called"] is True
    assert recorded["value"] is not None
    assert app_state.pan_offset_x != 0.0 or app_state.pan_offset_y != 0.0


def test_register_input_handlers_registers_mouse_handlers(monkeypatch):
    app_state = AppState()
    settings = DummySettings()
    session_state = {}
    calls = []

    monkeypatch.setattr(input_module.dpg, "does_item_exist", lambda tag: False)
    monkeypatch.setattr(input_module.dpg, "delete_item", lambda tag: calls.append(("delete", tag)))
    monkeypatch.setattr(input_module.dpg, "handler_registry", lambda *args, **kwargs: DummyRegistry(*args, **kwargs))
    monkeypatch.setattr(input_module.dpg, "add_mouse_click_handler", lambda **kwargs: calls.append(("click", kwargs)))
    monkeypatch.setattr(input_module.dpg, "add_mouse_wheel_handler", lambda **kwargs: calls.append(("wheel", kwargs)))
    monkeypatch.setattr(input_module.dpg, "add_mouse_drag_handler", lambda **kwargs: calls.append(("drag", kwargs)))
    monkeypatch.setattr(input_module.dpg, "add_mouse_release_handler", lambda **kwargs: calls.append(("release", kwargs)))
    monkeypatch.setattr(input_module.dpg, "is_key_down", lambda _key: False)
    monkeypatch.setattr(input_module.dpg, "get_mouse_pos", lambda local=False: (0, 0))

    input_module.register_input_handlers(app_state, settings, session_state)

    assert any(call[0] == "click" for call in calls)
    assert any(call[0] == "wheel" for call in calls)
    assert any(call[0] == "drag" for call in calls)
    assert any(call[0] == "release" for call in calls)
