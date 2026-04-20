"""Mouse interaction handlers for the WIIBBLE main canvas.

This module encapsulates click, drag, release, and wheel input logic so
that app.py can remain focused on session orchestration.
"""

import math

import dearpygui.dearpygui as dpg

from constants import (
    CURSOR_HIT_FRACTION,
    CURSOR_HIT_RADIUS_CIRCLE,
    PANEL_TOGGLE_BTN_SIZE,
    PANEL_W,
    ZOOM_MAX,
    ZOOM_MIN,
    ZOOM_SCALE,
    ZOOM_SPEED,
)
from ui import _on_zoom_change


def _handle_mouse_wheel(wheel_delta: float, app_state, session_state, settings) -> None:
    """Handle Ctrl+scroll zoom and pan around the current mouse position."""
    ctrl_held = dpg.is_key_down(dpg.mvKey_LControl)
    mouse_x, mouse_y = dpg.get_mouse_pos(local=False)
    if not ctrl_held:
        return  # plain scroll is reserved for future use

    cx = app_state.screen_width // 2 + app_state.pan_offset_x
    cy = app_state.screen_height // 2 + app_state.pan_offset_y
    logical_x = (mouse_x - cx) / settings.zoom_factor
    logical_y = (mouse_y - cy) / settings.zoom_factor

    try:
        slider_value = math.log(settings.zoom_factor) / math.log(ZOOM_SCALE)
    except (ValueError, ZeroDivisionError):
        slider_value = 0
    slider_value += wheel_delta * ZOOM_SPEED
    slider_value = max(ZOOM_MIN, min(ZOOM_MAX, slider_value))
    new_zoom = ZOOM_SCALE**slider_value

    new_pan_offset_x = mouse_x - (logical_x * new_zoom + app_state.screen_width // 2)
    new_pan_offset_y = mouse_y - (logical_y * new_zoom + app_state.screen_height // 2)
    app_state.pan_offset_x = new_pan_offset_x
    app_state.pan_offset_y = new_pan_offset_y

    dpg.set_value("zoom_slider", slider_value)
    _on_zoom_change(slider_value, settings, app_state)
    session_state["action"] = "pan_changed"


def _handle_canvas_click(mx: float, my: float, app_state, settings, session_state) -> None:
    """Handle left-click on the canvas, toggling cursor or starting a target."""
    if (
        (mx <= PANEL_TOGGLE_BTN_SIZE + 8 and my <= PANEL_TOGGLE_BTN_SIZE + 8)
        or (mx <= PANEL_W and session_state.get("toolbar_visible", False))
        or dpg.is_key_down(dpg.mvKey_LControl)
    ):
        return

    cursor_radius = (
        int(CURSOR_HIT_FRACTION * app_state.screen_height)
        if settings.cursor_mode == "avatar"
        else CURSOR_HIT_RADIUS_CIRCLE
    )
    dist = math.sqrt((mx - app_state.ball_x) ** 2 + (my - app_state.ball_y) ** 2)
    if dist <= cursor_radius:
        settings.toggle_cursor_mode()
        if hasattr(app_state, "update_cursor_toggle_label"):
            app_state.update_cursor_toggle_label()
        return

    cx = app_state.screen_width // 2 + app_state.pan_offset_x
    cy = app_state.screen_height // 2 + app_state.pan_offset_y
    logical_x = (mx - cx) / settings.zoom_factor
    logical_y = (my - cy) / settings.zoom_factor
    app_state.target_in_progress = {
        "center": (logical_x, logical_y),
        "radius": 5.0,
    }


def _handle_target_drag(app_state, settings):
    """Resize the target under construction while the mouse is dragged."""
    if app_state.target_in_progress is None:
        return
    mouse_x, mouse_y = dpg.get_mouse_pos(local=False)
    cx = app_state.screen_width // 2 + app_state.pan_offset_x
    cy = app_state.screen_height // 2 + app_state.pan_offset_y
    logical_x = (mouse_x - cx) / settings.zoom_factor
    logical_y = (mouse_y - cy) / settings.zoom_factor
    x0, y0 = app_state.target_in_progress["center"]
    new_radius = math.sqrt((logical_x - x0) ** 2 + (logical_y - y0) ** 2)
    app_state.target_in_progress["radius"] = max(1.0, new_radius)


def _handle_target_release(app_state):
    """Finalize the current target when the mouse button is released."""
    if app_state.target_in_progress is not None:
        app_state.clicked_locations.append(app_state.target_in_progress)
        app_state.target_in_progress = None


def _handle_pan_drag(app_state, session_state):
    """Handle Ctrl+drag panning of the main canvas."""
    if not dpg.is_key_down(dpg.mvKey_LControl):
        return
    mouse_x, mouse_y = dpg.get_mouse_pos(local=False)
    if not getattr(app_state, "is_panning", False):
        app_state.is_panning = True
        app_state.pan_start_mouse = (mouse_x, mouse_y)
        app_state.pan_start_offset = (app_state.pan_offset_x, app_state.pan_offset_y)
        return

    start_x, start_y = app_state.pan_start_mouse
    offset_x, offset_y = app_state.pan_start_offset
    dx = mouse_x - start_x
    dy = mouse_y - start_y
    app_state.pan_offset_x = offset_x + dx
    app_state.pan_offset_y = offset_y + dy
    session_state["action"] = "pan_changed"


def _handle_pan_release(app_state):
    """Stop panning when the mouse button is released."""
    if getattr(app_state, "is_panning", False):
        app_state.is_panning = False


def register_input_handlers(app_state, settings, session_state):
    """Register all mouse interaction handlers for the main session canvas."""
    if dpg.does_item_exist("click_handler"):
        dpg.delete_item("click_handler")
    with dpg.handler_registry(tag="click_handler"):
        dpg.add_mouse_click_handler(
            button=0,
            callback=lambda: _handle_canvas_click(
                *dpg.get_mouse_pos(local=False),
                app_state,
                settings,
                session_state,
            ),
        )
        dpg.add_mouse_wheel_handler(
            callback=lambda s, v: _handle_mouse_wheel(v, app_state, session_state, settings),
        )
        dpg.add_mouse_drag_handler(
            button=0,
            threshold=0,
            callback=lambda s, d: (
                _handle_pan_drag(app_state, session_state)
                if dpg.is_key_down(dpg.mvKey_LControl)
                else _handle_target_drag(app_state, settings)
            ),
        )
        dpg.add_mouse_release_handler(
            button=0,
            callback=lambda: (
                _handle_pan_release(app_state)
                if getattr(app_state, "is_panning", False)
                else _handle_target_release(app_state)
            ),
        )
