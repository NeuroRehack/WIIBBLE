"""Mouse interaction handlers for the WIIBBLE main canvas.

This module encapsulates click, drag, release, and wheel input logic so
that app.py can remain focused on session orchestration.
"""

from __future__ import annotations

import logging
import math
from typing import Any

import dearpygui.dearpygui as dpg

from wiibble.features.data_processing import logical_to_viewport, viewport_to_logical
from wiibble.ui.cursor_geometry import (
    logical_rect_to_viewport_bounds,
    pick_rect_edge,
    radius_from_center,
    screen_cursor_radius,
)
from wiibble.ui.ui import (
    _on_start_recording,
    _on_zoom_change,
    collapse_settings_panel,
    is_mouse_over_quick_access,
)
from wiibble.utils.constants import (
    CURSOR_DRAG_THRESHOLD,
    CURSOR_SIZE_MAX,
    CURSOR_SIZE_MIN,
    PANEL_W,
    TARGET_MIN_LOGICAL_SPAN,
    ZOOM_MAX,
    ZOOM_MIN,
    ZOOM_SCALE,
    ZOOM_SPEED,
)
from wiibble.utils.state import AppState, Settings

log = logging.getLogger(__name__)

SessionState = dict[str, Any]

_SETTINGS_INPUT_TAGS = (
    "body_weight_input",
    "record_duration_input",
    "board_cal_reference_input",
)


def _settings_input_active() -> bool:
    """Return True when focus is in a settings text field."""
    return any(
        dpg.does_item_exist(tag) and dpg.is_item_active(tag)
        for tag in _SETTINGS_INPUT_TAGS
    )


def _keyboard_shortcuts_allowed(session_state: SessionState) -> bool:
    """Return True when canvas keyboard shortcuts should fire."""
    if not session_state.get("toolbar_enabled"):
        return False
    return not _settings_input_active()


def _handle_clear_shortcut(session_state: SessionState) -> None:
    """Clear the canvas when Ctrl+Shift+C is pressed."""
    if not _keyboard_shortcuts_allowed(session_state):
        return
    if not dpg.is_key_down(dpg.mvKey_LControl) or not dpg.is_key_down(dpg.mvKey_LShift):
        return
    session_state["action"] = "clear"
    session_state["action_detail"] = "Ctrl+Shift+C"


def _handle_record_shortcut(
    app_state: AppState, settings: Settings, session_state: SessionState
) -> None:
    """Toggle recording when Ctrl+Space is pressed."""
    if not _keyboard_shortcuts_allowed(session_state):
        return
    if not dpg.is_key_down(dpg.mvKey_LControl):
        return
    _on_start_recording(app_state, settings, source="Ctrl+Space")


def _handle_mouse_wheel(
    wheel_delta: float,
    app_state: AppState,
    session_state: SessionState,
    settings: Settings,
) -> None:
    """Handle Ctrl+scroll zoom and pan around the current mouse position."""
    ctrl_held = dpg.is_key_down(dpg.mvKey_LControl)
    mouse_x, mouse_y = dpg.get_mouse_pos(local=False)
    if not ctrl_held:
        return  # plain scroll is reserved for future use

    cx = app_state.screen_width // 2 + app_state.pan_offset_x
    cy = app_state.screen_height // 2 + app_state.pan_offset_y
    logical_x, logical_y = viewport_to_logical(
        mouse_x,
        mouse_y,
        cx,
        cy,
        settings.zoom_factor,
        settings.flip_horizontal,
        settings.flip_vertical,
    )

    try:
        slider_value = math.log(settings.zoom_factor) / math.log(ZOOM_SCALE)
    except (ValueError, ZeroDivisionError):
        slider_value = 0
    slider_value += wheel_delta * ZOOM_SPEED
    slider_value = max(ZOOM_MIN, min(ZOOM_MAX, slider_value))
    new_zoom = ZOOM_SCALE**slider_value

    vx, vy = logical_to_viewport(
        logical_x,
        logical_y,
        app_state.screen_width // 2,
        app_state.screen_height // 2,
        new_zoom,
        settings.flip_horizontal,
        settings.flip_vertical,
    )
    new_pan_offset_x = mouse_x - vx
    new_pan_offset_y = mouse_y - vy
    app_state.pan_offset_x = new_pan_offset_x
    app_state.pan_offset_y = new_pan_offset_y

    dpg.set_value("zoom_slider", slider_value)
    _on_zoom_change(slider_value, settings, app_state, log_change=False)
    log.info("Zoom changed via Ctrl+scroll to %.2fx", new_zoom)
    session_state["action"] = "pan_changed"


def _viewport_center(app_state: AppState) -> tuple[float, float]:
    """Return the canvas centre in viewport pixels (including pan)."""
    cx = app_state.screen_width // 2 + app_state.pan_offset_x
    cy = app_state.screen_height // 2 + app_state.pan_offset_y
    return cx, cy


def _target_shape(target: dict[str, Any] | tuple[float, float]) -> str:
    """Return ``circle`` or ``rect`` for a finalized or in-progress target."""
    if isinstance(target, dict) and target.get("shape") == "rect":
        return "rect"
    return "circle"


def _target_logical_center(
    target: dict[str, Any] | tuple[float, float],
) -> tuple[float, float]:
    """Return the logical centre of a target (circle centre or rect centroid)."""
    if _target_shape(target) == "rect":
        min_pt = target["min"]
        max_pt = target["max"]
        return ((min_pt[0] + max_pt[0]) / 2, (min_pt[1] + max_pt[1]) / 2)
    if isinstance(target, dict):
        return target["center"]
    return target


def _translate_target(target: dict[str, Any], dx: float, dy: float) -> None:
    """Shift a target by a logical delta."""
    if isinstance(target, dict) and _target_shape(target) == "rect":
        min_x, min_y = target["min"]
        max_x, max_y = target["max"]
        target["min"] = (min_x + dx, min_y + dy)
        target["max"] = (max_x + dx, max_y + dy)
    elif isinstance(target, dict):
        lx, ly = target["center"]
        target["center"] = (lx + dx, ly + dy)


def _shift_held() -> bool:
    """Return True when either Shift modifier key is held."""
    return dpg.is_key_down(dpg.mvKey_ModShift)


def _radius_from_center(
    logical_x: float, logical_y: float, center_x: float, center_y: float
) -> float:
    """Return circle radius from centre to a logical point, with a minimum."""
    return radius_from_center(logical_x, logical_y, center_x, center_y)


def _pick_rect_edge(
    mx: float,
    my: float,
    target: dict[str, Any],
    app_state: AppState,
    settings: Settings,
) -> str:
    """Return the viewport edge nearest to (mx, my) for a rectangular target."""
    cx, cy = _viewport_center(app_state)
    return pick_rect_edge(mx, my, target, cx, cy, settings)


def _start_target_resize(
    idx: int,
    target: dict[str, Any],
    mx: float,
    my: float,
    app_state: AppState,
    settings: Settings,
) -> None:
    """Begin Shift+drag resize for an existing target."""
    shape = _target_shape(target)
    edge = (
        _pick_rect_edge(mx, my, target, app_state, settings)
        if shape == "rect"
        else None
    )
    app_state.target_resize_in_progress = {
        "index": idx,
        "shape": shape,
        "edge": edge,
    }
    log.info(
        "Target resize started (index=%d, shape=%s, edge=%s)",
        idx,
        shape,
        edge,
    )


def _logical_rect_to_viewport_bounds(
    min_pt: tuple[float, float],
    max_pt: tuple[float, float],
    cx: float,
    cy: float,
    zoom: float,
    flip_horizontal: bool,
    flip_vertical: bool,
) -> tuple[float, float, float, float]:
    """Convert logical rect corners to viewport min/max x/y (order-normalized)."""
    return logical_rect_to_viewport_bounds(
        min_pt, max_pt, cx, cy, zoom, flip_horizontal, flip_vertical
    )


def _point_hits_target(
    mx: float,
    my: float,
    target: dict[str, Any] | tuple[float, float],
    app_state: AppState,
    settings: Settings,
) -> bool:
    """Return True when viewport point (mx, my) is inside the target."""
    cx, cy = _viewport_center(app_state)
    zoom = settings.zoom_factor
    flip_h = settings.flip_horizontal
    flip_v = settings.flip_vertical
    if _target_shape(target) == "rect":
        min_vx, min_vy, max_vx, max_vy = _logical_rect_to_viewport_bounds(
            target["min"], target["max"], cx, cy, zoom, flip_h, flip_v
        )
        return min_vx <= mx <= max_vx and min_vy <= my <= max_vy
    if isinstance(target, dict):
        lx, ly = target["center"]
        logical_radius = target.get("radius", 5.0)
    else:
        lx, ly = target
        logical_radius = 5.0
    vx, vy = logical_to_viewport(lx, ly, cx, cy, zoom, flip_h, flip_v)
    scaled_radius = logical_radius * zoom
    dist = math.sqrt((mx - vx) ** 2 + (my - vy) ** 2)
    return dist <= scaled_radius


def _find_target_at(
    mx: float, my: float, app_state: AppState, settings: Settings
) -> int | None:
    """Return (index, target) for the first target hit at viewport coords, or None."""
    for idx, target in enumerate(app_state.clicked_locations):
        if _point_hits_target(mx, my, target, app_state, settings):
            return idx, target
    return None


def _handle_canvas_click(
    mx: float,
    my: float,
    app_state: AppState,
    settings: Settings,
    session_state: SessionState,
) -> None:
    """Handle left-click on the canvas, starting cursor drag/resize or a new target."""
    if dpg.does_item_exist("recording_dir_dialog") and dpg.is_item_shown(
        "recording_dir_dialog"
    ):
        return

    if session_state.get("toolbar_visible", False):
        if mx <= PANEL_W or is_mouse_over_quick_access():
            return
        collapse_settings_panel(session_state, source="canvas click")
        return

    if is_mouse_over_quick_access() or dpg.is_key_down(dpg.mvKey_LControl):
        return

    cursor_radius = screen_cursor_radius(settings)
    dist = math.sqrt((mx - app_state.ball_x) ** 2 + (my - app_state.ball_y) ** 2)
    if dist <= cursor_radius:
        log.info("Cursor resize drag started")
        app_state.cursor_drag_in_progress = True
        app_state.cursor_drag_start_size = settings.cursor_size
        return

    cx = app_state.screen_width // 2 + app_state.pan_offset_x
    cy = app_state.screen_height // 2 + app_state.pan_offset_y
    logical_x, logical_y = viewport_to_logical(
        mx,
        my,
        cx,
        cy,
        settings.zoom_factor,
        settings.flip_horizontal,
        settings.flip_vertical,
    )

    hit = _find_target_at(mx, my, app_state, settings)
    if hit is not None:
        idx, target = hit
        if _shift_held():
            _start_target_resize(idx, target, mx, my, app_state, settings)
            return
        log.info("Target move started (index=%d)", idx)
        tcx, tcy = _target_logical_center(target)
        app_state.target_move_in_progress = {
            "index": idx,
            "grab_offset": (logical_x - tcx, logical_y - tcy),
        }
        return

    default_radius = float(settings.cursor_size)
    if dpg.is_key_down(dpg.mvKey_R):
        log.info(
            "Target placement started (rectangle) at (%.1f, %.1f)",
            logical_x,
            logical_y,
        )
        app_state.target_in_progress = {
            "shape": "rect",
            "anchor": (logical_x, logical_y),
            "min": (logical_x, logical_y),
            "max": (logical_x, logical_y),
            "drag_started": False,
            "click_screen": (mx, my),
        }
        return

    log.info(
        "Target placement started (circle) at (%.1f, %.1f)",
        logical_x,
        logical_y,
    )
    app_state.target_in_progress = {
        "center": (logical_x, logical_y),
        "radius": default_radius,
        "drag_started": False,
        "click_screen": (mx, my),
    }


def _handle_cursor_drag(app_state: AppState, settings: Settings) -> None:
    """Resize the cursor while the mouse is dragged from the cursor position."""
    if not getattr(app_state, "cursor_drag_in_progress", False):
        return
    mouse_x, mouse_y = dpg.get_mouse_pos(local=False)
    dist = math.sqrt(
        (mouse_x - app_state.ball_x) ** 2 + (mouse_y - app_state.ball_y) ** 2
    )
    new_size = int(max(CURSOR_SIZE_MIN, min(CURSOR_SIZE_MAX, dist)))
    settings.cursor_size = new_size
    if dpg.does_item_exist("cursor_size_slider"):
        dpg.set_value("cursor_size_slider", new_size)


def _handle_cursor_release(app_state: AppState, settings: Settings) -> None:
    """Finalise cursor drag: save new size if it changed, otherwise restore."""
    if not getattr(app_state, "cursor_drag_in_progress", False):
        return
    size_delta = abs(settings.cursor_size - app_state.cursor_drag_start_size)
    if size_delta >= CURSOR_DRAG_THRESHOLD:
        log.info(
            "Cursor size changed via drag: %d → %d px",
            app_state.cursor_drag_start_size,
            settings.cursor_size,
        )
        settings.save()
    else:
        settings.cursor_size = app_state.cursor_drag_start_size
        if dpg.does_item_exist("cursor_size_slider"):
            dpg.set_value("cursor_size_slider", settings.cursor_size)
    app_state.cursor_drag_in_progress = False


def _handle_target_drag(app_state: AppState, settings: Settings) -> None:
    """Resize the target under construction while the mouse is dragged."""
    tip = app_state.target_in_progress
    if tip is None:
        return
    mouse_x, mouse_y = dpg.get_mouse_pos(local=False)
    # Only begin resizing once the mouse has moved meaningfully from the click point.
    if not tip.get("drag_started", False):
        cx0, cy0 = tip.get("click_screen", (mouse_x, mouse_y))
        if (
            math.sqrt((mouse_x - cx0) ** 2 + (mouse_y - cy0) ** 2)
            < CURSOR_DRAG_THRESHOLD
        ):
            return
        tip["drag_started"] = True
    cx = app_state.screen_width // 2 + app_state.pan_offset_x
    cy = app_state.screen_height // 2 + app_state.pan_offset_y
    logical_x, logical_y = viewport_to_logical(
        mouse_x,
        mouse_y,
        cx,
        cy,
        settings.zoom_factor,
        settings.flip_horizontal,
        settings.flip_vertical,
    )
    if tip.get("shape") == "rect":
        ax, ay = tip["anchor"]
        tip["min"] = (min(ax, logical_x), min(ay, logical_y))
        tip["max"] = (max(ax, logical_x), max(ay, logical_y))
        return
    x0, y0 = tip["center"]
    tip["radius"] = _radius_from_center(logical_x, logical_y, x0, y0)


def _handle_target_resize_drag(app_state: AppState, settings: Settings) -> None:
    """Resize an existing target while Shift+drag is in progress."""
    resize = app_state.target_resize_in_progress
    if resize is None:
        return
    idx = resize["index"]
    if idx >= len(app_state.clicked_locations):
        app_state.target_resize_in_progress = None
        return
    mouse_x, mouse_y = dpg.get_mouse_pos(local=False)
    cx = app_state.screen_width // 2 + app_state.pan_offset_x
    cy = app_state.screen_height // 2 + app_state.pan_offset_y
    logical_x, logical_y = viewport_to_logical(
        mouse_x,
        mouse_y,
        cx,
        cy,
        settings.zoom_factor,
        settings.flip_horizontal,
        settings.flip_vertical,
    )
    target = app_state.clicked_locations[idx]
    if resize["shape"] == "circle":
        center_x, center_y = target["center"]
        target["radius"] = _radius_from_center(logical_x, logical_y, center_x, center_y)
        return
    min_x, min_y = target["min"]
    max_x, max_y = target["max"]
    edge = resize["edge"]
    min_span = TARGET_MIN_LOGICAL_SPAN
    if edge == "left":
        target["min"] = (min(logical_x, max_x - min_span), min_y)
    elif edge == "right":
        target["max"] = (max(logical_x, min_x + min_span), max_y)
    elif edge == "top":
        target["min"] = (min_x, min(logical_y, max_y - min_span))
    elif edge == "bottom":
        target["max"] = (max_x, max(logical_y, min_y + min_span))


def _handle_target_resize_release(app_state: AppState) -> None:
    """Finalize target resize when the mouse button is released."""
    if app_state.target_resize_in_progress is not None:
        log.info(
            "Target resized (index=%d)",
            app_state.target_resize_in_progress["index"],
        )
    app_state.target_resize_in_progress = None


def _handle_target_move_drag(app_state: AppState, settings: Settings) -> None:
    """Reposition an existing target while the mouse is dragged."""
    move = app_state.target_move_in_progress
    if move is None:
        return
    idx = move["index"]
    if idx >= len(app_state.clicked_locations):
        app_state.target_move_in_progress = None
        return
    mouse_x, mouse_y = dpg.get_mouse_pos(local=False)
    cx = app_state.screen_width // 2 + app_state.pan_offset_x
    cy = app_state.screen_height // 2 + app_state.pan_offset_y
    logical_x, logical_y = viewport_to_logical(
        mouse_x,
        mouse_y,
        cx,
        cy,
        settings.zoom_factor,
        settings.flip_horizontal,
        settings.flip_vertical,
    )
    grab_dx, grab_dy = move["grab_offset"]
    new_center = (logical_x - grab_dx, logical_y - grab_dy)
    target = app_state.clicked_locations[idx]
    old_center = _target_logical_center(target)
    dx = new_center[0] - old_center[0]
    dy = new_center[1] - old_center[1]
    if isinstance(target, dict):
        _translate_target(target, dx, dy)
    else:
        app_state.clicked_locations[idx] = {
            "center": (target[0] + dx, target[1] + dy),
            "radius": 5.0,
        }


def _handle_target_move_release(app_state: AppState) -> None:
    """Finalize target reposition when the mouse button is released."""
    if app_state.target_move_in_progress is not None:
        log.info(
            "Target moved (index=%d)",
            app_state.target_move_in_progress["index"],
        )
    app_state.target_move_in_progress = None


def _handle_target_release(app_state: AppState, settings: Settings) -> None:
    """Finalize the current target when the mouse button is released."""
    tip = app_state.target_in_progress
    if tip is None:
        return
    if tip.get("shape") == "rect":
        if not tip.get("drag_started", False):
            ax, ay = tip["anchor"]
            half = float(settings.cursor_size)
            tip["min"] = (ax - half, ay - half)
            tip["max"] = (ax + half, ay + half)
        for key in ("click_screen", "drag_started", "anchor"):
            tip.pop(key, None)
    else:
        for key in ("click_screen", "drag_started"):
            tip.pop(key, None)
    app_state.clicked_locations.append(tip)
    app_state.target_in_progress = None
    if tip.get("shape") == "rect":
        min_pt, max_pt = tip["min"], tip["max"]
        log.info(
            "Target placed (rectangle, bounds=(%.1f,%.1f)-(%.1f,%.1f))",
            min_pt[0],
            min_pt[1],
            max_pt[0],
            max_pt[1],
        )
    else:
        center = tip["center"]
        log.info(
            "Target placed (circle, center=(%.1f,%.1f), radius=%.1f)",
            center[0],
            center[1],
            tip.get("radius", 5.0),
        )


def _handle_pan_drag(app_state: AppState, session_state: SessionState) -> None:
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


def _handle_pan_release(app_state: AppState) -> None:
    """Stop panning when the mouse button is released."""
    if getattr(app_state, "is_panning", False):
        log.info(
            "Canvas pan offset set to (%.0f, %.0f)",
            app_state.pan_offset_x,
            app_state.pan_offset_y,
        )
        app_state.is_panning = False


def _handle_right_click(
    mx: float, my: float, app_state: AppState, settings: Settings
) -> None:
    """Remove a target when right-clicking inside it."""
    hit = _find_target_at(mx, my, app_state, settings)
    if hit is not None:
        idx, target = hit
        app_state.clicked_locations.remove(target)
        log.info("Target removed (index=%d)", idx)


def register_input_handlers(
    app_state: AppState, settings: Settings, session_state: SessionState
) -> None:
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
            callback=lambda s, v: _handle_mouse_wheel(
                v, app_state, session_state, settings
            ),
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
                    else (
                        _handle_target_resize_drag(app_state, settings)
                        if getattr(app_state, "target_resize_in_progress", None)
                        is not None
                        else (
                            _handle_target_move_drag(app_state, settings)
                            if getattr(app_state, "target_move_in_progress", None)
                            is not None
                            else _handle_target_drag(app_state, settings)
                        )
                    )
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
                    else (
                        _handle_target_resize_release(app_state)
                        if getattr(app_state, "target_resize_in_progress", None)
                        is not None
                        else (
                            _handle_target_move_release(app_state)
                            if getattr(app_state, "target_move_in_progress", None)
                            is not None
                            else _handle_target_release(app_state, settings)
                        )
                    )
                )
            ),
        )
        dpg.add_key_press_handler(
            key=dpg.mvKey_C,
            callback=lambda: _handle_clear_shortcut(session_state),
        )
        dpg.add_key_press_handler(
            key=dpg.mvKey_Spacebar,
            callback=lambda: _handle_record_shortcut(
                app_state, settings, session_state
            ),
        )
