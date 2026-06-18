import math

import wiibble.ui.input as input_module
from wiibble.utils.state import AppState


class DummySettings:
    def __init__(self, cursor_mode="avatar", zoom_factor=1.0, cursor_size=20):
        self.cursor_mode = cursor_mode
        self.zoom_factor = zoom_factor
        self.cursor_size = cursor_size
        self.flip_horizontal = False
        self.flip_vertical = False
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
    settings = DummySettings(cursor_mode="avatar", cursor_size=20)
    session_state = {"toolbar_visible": False}
    monkeypatch.setattr(input_module.dpg, "is_key_down", lambda _key: False)
    monkeypatch.setattr(input_module.dpg, "does_item_exist", lambda _tag: False)
    monkeypatch.setattr(input_module, "is_mouse_over_quick_access", lambda: False)

    # Click starts the drag; a tiny release (no drag) should toggle the mode
    input_module._handle_canvas_click(100, 50, app_state, settings, session_state)
    assert app_state.cursor_drag_in_progress is True

    # Release without dragging — size unchanged, so toggle fires
    input_module._handle_cursor_release(app_state, settings)

    assert settings.cursor_mode == "circle"
    assert settings.toggled is True
    assert app_state.cursor_drag_in_progress is False
    assert app_state.target_in_progress is None


def test_handle_canvas_click_starts_target_when_click_off_cursor(monkeypatch):
    app_state = AppState(screen_width=200, screen_height=100, ball_x=0, ball_y=0)
    settings = DummySettings(cursor_mode="circle", zoom_factor=1.0, cursor_size=20)
    session_state = {"toolbar_visible": False}
    monkeypatch.setattr(input_module.dpg, "is_key_down", lambda _key: False)
    monkeypatch.setattr(input_module.dpg, "does_item_exist", lambda _tag: False)
    monkeypatch.setattr(input_module.dpg, "is_item_shown", lambda _tag: False)
    monkeypatch.setattr(input_module, "is_mouse_over_quick_access", lambda: False)

    input_module._handle_canvas_click(150, 75, app_state, settings, session_state)

    assert app_state.target_in_progress is not None
    assert app_state.target_in_progress["center"] == (50.0, 25.0)
    assert app_state.target_in_progress["radius"] == 20.0


def _click_suppression_monkeypatch(monkeypatch):
    monkeypatch.setattr(input_module.dpg, "is_key_down", lambda _key: False)
    monkeypatch.setattr(input_module.dpg, "does_item_exist", lambda _tag: False)
    monkeypatch.setattr(input_module.dpg, "is_item_shown", lambda _tag: False)
    monkeypatch.setattr(input_module, "is_mouse_over_quick_access", lambda: False)


def test_handle_canvas_click_starts_target_move_when_click_on_target(monkeypatch):
    app_state = AppState(screen_width=200, screen_height=100, ball_x=0, ball_y=0)
    app_state.clicked_locations = [{"center": (50.0, 25.0), "radius": 20.0}]
    settings = DummySettings(cursor_mode="circle", zoom_factor=1.0, cursor_size=20)
    session_state = {"toolbar_visible": False}
    _click_suppression_monkeypatch(monkeypatch)

    input_module._handle_canvas_click(150, 75, app_state, settings, session_state)

    assert app_state.target_move_in_progress is not None
    assert app_state.target_move_in_progress["index"] == 0
    assert app_state.target_move_in_progress["grab_offset"] == (0.0, 0.0)
    assert app_state.target_in_progress is None


def test_handle_target_move_drag_updates_target_center(monkeypatch):
    app_state = AppState(screen_width=200, screen_height=100)
    app_state.clicked_locations = [{"center": (50.0, 25.0), "radius": 20.0}]
    app_state.target_move_in_progress = {"index": 0, "grab_offset": (0.0, 0.0)}
    settings = DummySettings(zoom_factor=1.0)
    monkeypatch.setattr(input_module.dpg, "get_mouse_pos", lambda local=False: (160, 85))

    input_module._handle_target_move_drag(app_state, settings)

    assert app_state.clicked_locations[0]["center"] == (60.0, 35.0)


def test_handle_target_move_release_clears_move_state():
    app_state = AppState()
    app_state.clicked_locations = [{"center": (60.0, 35.0), "radius": 20.0}]
    app_state.target_move_in_progress = {"index": 0, "grab_offset": (0.0, 0.0)}

    input_module._handle_target_move_release(app_state)

    assert app_state.target_move_in_progress is None
    assert app_state.clicked_locations[0]["center"] == (60.0, 35.0)


def test_handle_target_move_click_without_drag_leaves_center_unchanged(monkeypatch):
    app_state = AppState(screen_width=200, screen_height=100, ball_x=0, ball_y=0)
    app_state.clicked_locations = [{"center": (50.0, 25.0), "radius": 20.0}]
    settings = DummySettings(cursor_mode="circle", zoom_factor=1.0, cursor_size=20)
    session_state = {"toolbar_visible": False}
    _click_suppression_monkeypatch(monkeypatch)

    input_module._handle_canvas_click(150, 75, app_state, settings, session_state)
    input_module._handle_target_move_release(app_state)

    assert app_state.target_move_in_progress is None
    assert app_state.clicked_locations[0]["center"] == (50.0, 25.0)


def test_handle_target_drag_updates_target_radius(monkeypatch):
    app_state = AppState(screen_width=200, screen_height=100)
    app_state.target_in_progress = {"center": (0.0, 0.0), "radius": 5.0, "drag_started": True}
    settings = DummySettings(zoom_factor=1.0)
    monkeypatch.setattr(input_module.dpg, "get_mouse_pos", lambda local=False: (110, 50))

    input_module._handle_target_drag(app_state, settings)

    assert math.isclose(app_state.target_in_progress["radius"], 10.0, rel_tol=1e-6)


def test_handle_target_release_appends_target():
    app_state = AppState()
    settings = DummySettings(cursor_size=20)
    app_state.target_in_progress = {"center": (4.0, 2.0), "radius": 5.0}

    input_module._handle_target_release(app_state, settings)

    assert app_state.target_in_progress is None
    assert app_state.clicked_locations == [{"center": (4.0, 2.0), "radius": 5.0}]


def test_handle_canvas_click_starts_rect_target_when_r_held(monkeypatch):
    app_state = AppState(screen_width=200, screen_height=100, ball_x=0, ball_y=0)
    settings = DummySettings(cursor_mode="circle", zoom_factor=1.0, cursor_size=20)
    session_state = {"toolbar_visible": False}
    monkeypatch.setattr(
        input_module.dpg, "is_key_down", lambda key: key == input_module.dpg.mvKey_R
    )
    monkeypatch.setattr(input_module.dpg, "does_item_exist", lambda _tag: False)
    monkeypatch.setattr(input_module.dpg, "is_item_shown", lambda _tag: False)
    monkeypatch.setattr(input_module, "is_mouse_over_quick_access", lambda: False)

    input_module._handle_canvas_click(150, 75, app_state, settings, session_state)

    assert app_state.target_in_progress is not None
    assert app_state.target_in_progress["shape"] == "rect"
    assert app_state.target_in_progress["anchor"] == (50.0, 25.0)
    assert app_state.target_in_progress["min"] == (50.0, 25.0)
    assert app_state.target_in_progress["max"] == (50.0, 25.0)


def test_handle_target_drag_updates_rect_bounds(monkeypatch):
    app_state = AppState(screen_width=200, screen_height=100)
    app_state.target_in_progress = {
        "shape": "rect",
        "anchor": (0.0, 0.0),
        "min": (0.0, 0.0),
        "max": (0.0, 0.0),
        "drag_started": True,
        "click_screen": (100, 50),
    }
    settings = DummySettings(zoom_factor=1.0)
    monkeypatch.setattr(input_module.dpg, "get_mouse_pos", lambda local=False: (110, 55))

    input_module._handle_target_drag(app_state, settings)

    assert app_state.target_in_progress["min"] == (0.0, 0.0)
    assert app_state.target_in_progress["max"] == (10.0, 5.0)


def test_handle_target_release_appends_default_rect_without_drag():
    app_state = AppState()
    settings = DummySettings(cursor_size=20)
    app_state.target_in_progress = {
        "shape": "rect",
        "anchor": (50.0, 25.0),
        "min": (50.0, 25.0),
        "max": (50.0, 25.0),
        "drag_started": False,
        "click_screen": (150, 75),
    }

    input_module._handle_target_release(app_state, settings)

    assert app_state.target_in_progress is None
    assert app_state.clicked_locations == [
        {"shape": "rect", "min": (30.0, 5.0), "max": (70.0, 45.0)}
    ]


def test_find_target_at_hits_rect_target():
    app_state = AppState(screen_width=200, screen_height=100)
    app_state.clicked_locations = [
        {"shape": "rect", "min": (30.0, 5.0), "max": (70.0, 45.0)}
    ]
    settings = DummySettings(zoom_factor=1.0)

    hit = input_module._find_target_at(150, 75, app_state, settings)

    assert hit is not None
    assert hit[0] == 0


def test_handle_target_move_drag_translates_rect(monkeypatch):
    app_state = AppState(screen_width=200, screen_height=100)
    app_state.clicked_locations = [
        {"shape": "rect", "min": (0.0, 0.0), "max": (20.0, 20.0)}
    ]
    app_state.target_move_in_progress = {"index": 0, "grab_offset": (0.0, 0.0)}
    settings = DummySettings(zoom_factor=1.0)
    monkeypatch.setattr(input_module.dpg, "get_mouse_pos", lambda local=False: (120, 70))

    input_module._handle_target_move_drag(app_state, settings)

    assert app_state.clicked_locations[0]["min"] == (10.0, 10.0)
    assert app_state.clicked_locations[0]["max"] == (30.0, 30.0)


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
    monkeypatch.setattr(
        input_module.dpg, "set_value", lambda tag, value: recorded.update({"value": value})
    )
    monkeypatch.setattr(
        input_module,
        "_on_zoom_change",
        lambda slider_value, settings_, app_state_: recorded.update({"zoom_called": True}),
    )

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
    monkeypatch.setattr(
        input_module.dpg, "handler_registry", lambda *args, **kwargs: DummyRegistry(*args, **kwargs)
    )
    monkeypatch.setattr(
        input_module.dpg,
        "add_mouse_click_handler",
        lambda **kwargs: calls.append(("click", kwargs)),
    )
    monkeypatch.setattr(
        input_module.dpg,
        "add_mouse_wheel_handler",
        lambda **kwargs: calls.append(("wheel", kwargs)),
    )
    monkeypatch.setattr(
        input_module.dpg, "add_mouse_drag_handler", lambda **kwargs: calls.append(("drag", kwargs))
    )
    monkeypatch.setattr(
        input_module.dpg,
        "add_mouse_release_handler",
        lambda **kwargs: calls.append(("release", kwargs)),
    )
    monkeypatch.setattr(
        input_module.dpg,
        "add_key_press_handler",
        lambda **kwargs: calls.append(("key", kwargs)),
    )
    monkeypatch.setattr(input_module.dpg, "is_key_down", lambda _key: False)
    monkeypatch.setattr(input_module.dpg, "get_mouse_pos", lambda local=False: (0, 0))

    input_module.register_input_handlers(app_state, settings, session_state)

    assert any(call[0] == "click" for call in calls)
    assert any(call[0] == "wheel" for call in calls)
    assert any(call[0] == "drag" for call in calls)
    assert any(call[0] == "release" for call in calls)
    assert any(call[0] == "key" for call in calls)


def test_handle_canvas_click_suppressed_over_quick_access(monkeypatch):
    app_state = AppState(screen_width=200, screen_height=100, ball_x=0, ball_y=0)
    settings = DummySettings()
    session_state = {"toolbar_visible": False}
    monkeypatch.setattr(input_module.dpg, "is_key_down", lambda _key: False)
    monkeypatch.setattr(input_module.dpg, "does_item_exist", lambda _tag: False)
    monkeypatch.setattr(input_module.dpg, "is_item_shown", lambda _tag: False)
    monkeypatch.setattr(input_module, "is_mouse_over_quick_access", lambda: True)

    input_module._handle_canvas_click(10, 10, app_state, settings, session_state)

    assert app_state.target_in_progress is None
    assert app_state.cursor_drag_in_progress is False


def test_clear_shortcut_sets_action_when_allowed(monkeypatch):
    session_state = {"toolbar_enabled": True, "action": None}
    monkeypatch.setattr(input_module.dpg, "is_key_down", lambda key: True)
    monkeypatch.setattr(input_module.dpg, "does_item_exist", lambda tag: False)

    input_module._handle_clear_shortcut(session_state)

    assert session_state["action"] == "clear"


def test_clear_shortcut_ignored_when_toolbar_disabled(monkeypatch):
    session_state = {"toolbar_enabled": False, "action": None}
    monkeypatch.setattr(input_module.dpg, "is_key_down", lambda key: True)
    monkeypatch.setattr(input_module.dpg, "does_item_exist", lambda tag: False)

    input_module._handle_clear_shortcut(session_state)

    assert session_state["action"] is None


def test_clear_shortcut_ignored_when_settings_input_active(monkeypatch):
    session_state = {"toolbar_enabled": True, "action": None}
    monkeypatch.setattr(input_module.dpg, "is_key_down", lambda key: True)
    monkeypatch.setattr(input_module.dpg, "does_item_exist", lambda tag: tag == "body_weight_input")
    monkeypatch.setattr(input_module.dpg, "is_item_active", lambda tag: tag == "body_weight_input")

    input_module._handle_clear_shortcut(session_state)

    assert session_state["action"] is None


def test_record_shortcut_calls_start_recording_when_allowed(monkeypatch):
    app_state = AppState()
    settings = DummySettings()
    session_state = {"toolbar_enabled": True}
    called = {"value": False}
    monkeypatch.setattr(input_module.dpg, "is_key_down", lambda key: key == input_module.dpg.mvKey_LControl)
    monkeypatch.setattr(input_module.dpg, "does_item_exist", lambda tag: False)
    monkeypatch.setattr(
        input_module,
        "_on_start_recording",
        lambda a, s: called.update({"value": True}),
    )

    input_module._handle_record_shortcut(app_state, settings, session_state)

    assert called["value"] is True


def test_record_shortcut_ignored_without_ctrl(monkeypatch):
    app_state = AppState()
    settings = DummySettings()
    session_state = {"toolbar_enabled": True}
    called = {"value": False}
    monkeypatch.setattr(input_module.dpg, "is_key_down", lambda key: False)
    monkeypatch.setattr(input_module.dpg, "does_item_exist", lambda tag: False)
    monkeypatch.setattr(
        input_module,
        "_on_start_recording",
        lambda a, s: called.update({"value": True}),
    )

    input_module._handle_record_shortcut(app_state, settings, session_state)

    assert called["value"] is False
