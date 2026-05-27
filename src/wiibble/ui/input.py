"""Mouse interaction handlers for the WIIBBLE main canvas.

This module encapsulates click, drag, release, and wheel input logic so
that app.py can remain focused on session orchestration.
"""

import math

import dearpygui.dearpygui as dpg

from wiibble.ui.ui import _on_zoom_change
from wiibble.utils.constants import (
    CURSOR_DRAG_THRESHOLD,
    CURSOR_HIT_FRACTION,
    CURSOR_SIZE_MAX,
    CURSOR_SIZE_MIN,
    PANEL_TOGGLE_BTN_SIZE,
    PANEL_W,
    ZOOM_MAX,
    ZOOM_MIN,
    ZOOM_SCALE,
    ZOOM_SPEED,
)


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
    """Handle left-click on the canvas, starting cursor drag/resize or a new target."""
    # Suppress canvas click if mouse is over any UI element (e.g., settings panel, dialogs)
    if (
        (mx <= PANEL_TOGGLE_BTN_SIZE + 8 and my <= PANEL_TOGGLE_BTN_SIZE + 8)
        or (mx <= PANEL_W and session_state.get("toolbar_visible", False))
        or dpg.is_key_down(dpg.mvKey_LControl)
        or (
            dpg.does_item_exist("recording_dir_dialog")
            and dpg.is_item_shown("recording_dir_dialog")
        )
    ):
        return

    cursor_radius = (
        int(CURSOR_HIT_FRACTION * app_state.screen_height)
        if settings.cursor_mode == "avatar"
        else int(settings.cursor_size * settings.zoom_factor)
    )
    dist = math.sqrt((mx - app_state.ball_x) ** 2 + (my - app_state.ball_y) ** 2)
    if dist <= cursor_radius:
        # Begin cursor drag — mode toggle is decided on release based on drag distance
        app_state.cursor_drag_in_progress = True
        app_state.cursor_drag_start_size = settings.cursor_size
        return

    cx = app_state.screen_width // 2 + app_state.pan_offset_x
    cy = app_state.screen_height // 2 + app_state.pan_offset_y
    logical_x = (mx - cx) / settings.zoom_factor
    logical_y = (my - cy) / settings.zoom_factor
    # cursor_size is in logical units; no division needed — target matches cursor at any zoom
    default_radius = float(settings.cursor_size)
    app_state.target_in_progress = {
        "center": (logical_x, logical_y),
        "radius": default_radius,
        "drag_started": False,
        "click_screen": (mx, my),
    }


def _handle_cursor_drag(app_state, settings) -> None:
    """Resize the circle cursor while the mouse is dragged from the cursor position."""
    if not getattr(app_state, "cursor_drag_in_progress", False):
        return
    mouse_x, mouse_y = dpg.get_mouse_pos(local=False)
    dist = math.sqrt((mouse_x - app_state.ball_x) ** 2 + (mouse_y - app_state.ball_y) ** 2)
    # dist is in screen pixels; divide by zoom so cursor_size stays in logical units
    new_size = int(max(CURSOR_SIZE_MIN, min(CURSOR_SIZE_MAX, dist / settings.zoom_factor)))
    settings.cursor_size = new_size
    if dpg.does_item_exist("cursor_size_slider"):
        dpg.set_value("cursor_size_slider", new_size)


def _handle_cursor_release(app_state, settings) -> None:
    """Finalise cursor drag: toggle mode if barely moved, otherwise save new size."""
    if not getattr(app_state, "cursor_drag_in_progress", False):
        return
    size_delta = abs(settings.cursor_size - app_state.cursor_drag_start_size)
    if size_delta < CURSOR_DRAG_THRESHOLD:
        # Treat as a click — toggle cursor mode
        settings.toggle_cursor_mode()
        # Restore size (drag was tiny, probably unintentional)
        settings.cursor_size = app_state.cursor_drag_start_size
        if dpg.does_item_exist("cursor_size_slider"):
            dpg.set_value("cursor_size_slider", settings.cursor_size)
        if hasattr(app_state, "update_cursor_toggle_label"):
            app_state.update_cursor_toggle_label()
    else:
        settings.save()
    app_state.cursor_drag_in_progress = False


def _handle_target_drag(app_state, settings):
    """Resize the target under construction while the mouse is dragged."""
    tip = app_state.target_in_progress
    if tip is None:
        return
    mouse_x, mouse_y = dpg.get_mouse_pos(local=False)
    # Only begin resizing once the mouse has moved meaningfully from the click point.
    if not tip.get("drag_started", False):
        cx0, cy0 = tip.get("click_screen", (mouse_x, mouse_y))
        if math.sqrt((mouse_x - cx0) ** 2 + (mouse_y - cy0) ** 2) < CURSOR_DRAG_THRESHOLD:
            return
        tip["drag_started"] = True
    cx = app_state.screen_width // 2 + app_state.pan_offset_x
    cy = app_state.screen_height // 2 + app_state.pan_offset_y
    logical_x = (mouse_x - cx) / settings.zoom_factor
    logical_y = (mouse_y - cy) / settings.zoom_factor
    x0, y0 = tip["center"]
    new_radius = math.sqrt((logical_x - x0) ** 2 + (logical_y - y0) ** 2)
    tip["radius"] = max(1.0, new_radius)


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


def _handle_right_click(mx: float, my: float, app_state, settings) -> None:
    """Remove a target when right-clicking inside it."""
    cx = app_state.screen_width // 2 + app_state.pan_offset_x
    cy = app_state.screen_height // 2 + app_state.pan_offset_y
    for target in list(app_state.clicked_locations):
        if isinstance(target, dict):
            lx, ly = target["center"]
            logical_radius = target.get("radius", 5.0)
        else:
            lx, ly = target
            logical_radius = 5.0
        vx = cx + lx * settings.zoom_factor
        vy = cy + ly * settings.zoom_factor
        scaled_radius = logical_radius * settings.zoom_factor
        dist = math.sqrt((mx - vx) ** 2 + (my - vy) ** 2)
        if dist <= scaled_radius:
            app_state.clicked_locations.remove(target)
            break


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
        dpg.add_mouse_click_handler(
            button=1,
            callback=lambda: _handle_right_click(
                *dpg.get_mouse_pos(local=False),
                app_state,
                settings,
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
                else (
                    _handle_cursor_drag(app_state, settings)
                    if getattr(app_state, "cursor_drag_in_progress", False)
                    else _handle_target_drag(app_state, settings)
                )
            ),
        )
        dpg.add_mouse_release_handler(
            button=0,
            callback=lambda: (
                _handle_pan_release(app_state)
                if getattr(app_state, "is_panning", False)
                else (
                    _handle_cursor_release(app_state, settings)
                    if getattr(app_state, "cursor_drag_in_progress", False)
                    else _handle_target_release(app_state)
                )
            ),
        )
