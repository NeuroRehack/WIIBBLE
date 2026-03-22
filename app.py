# app.py
import math
import dearpygui.dearpygui as dpg
import hid
from board_connection import try_connection

from constants       import VENDOR_ID, PRODUCT_ID, DLL_RELATIVE_PATH
from resources       import ICON_PATH, resource_path
from data_processing import read_data, parse_data, tare, calculate_coordinates
from calibration     import wait_for_tare, sensitivity_calibration
from ui              import (draw_main_screen, draw_connection_screen,
                             draw_connection_failed_screen, ensure_textures_loaded)
from mock_board      import MockHIDDevice


# ---------------------------------------------------------------------------
# Board connection
# ---------------------------------------------------------------------------

def connect_wii_board(use_mock: bool = False, mock_scenario: str = "sway"):
    """Return an open HID device (real or mock)."""
    if use_mock:
        device = MockHIDDevice.from_scenario(mock_scenario)
        device.open(VENDOR_ID, PRODUCT_ID)
        print(f"[MOCK] Using MockHIDDevice (scenario: {mock_scenario})")
        return device
    try:
        print("Connecting to Wii Balance Board...")
        device = hid.device()
        device.open(VENDOR_ID, PRODUCT_ID)
        print("Connected successfully!")
        return device
    except IOError as e:
        print(f"Failed to connect: {e}")
        return None


def _try_connection_loop(dl, app_state, use_mock: bool = False) -> bool:
    """
    Show connection screen and loop until board connects.
    Returns True on success, False if window closed.
    Skipped entirely in mock mode.
    """
    if use_mock:
        print("[MOCK] Skipping connection screen.")
        return True

    while dpg.is_dearpygui_running():
        # Show "Trying to connect" while attempting
        dpg.delete_item(dl, children_only=True)
        draw_connection_screen(dl, app_state)
        dpg.render_dearpygui_frame()

        result = try_connection(resource_path(DLL_RELATIVE_PATH))
        if result == 0:
            return True

        # Show failed screen and wait for Enter key
        while dpg.is_dearpygui_running():
            dpg.delete_item(dl, children_only=True)
            draw_connection_failed_screen(dl, app_state)
            dpg.render_dearpygui_frame()
            if dpg.is_key_pressed(dpg.mvKey_Return):
                # Show retrying feedback immediately before next attempt
                dpg.delete_item(dl, children_only=True)
                draw_connection_screen(dl, app_state)
                dpg.render_dearpygui_frame()
                break

    return False


# ---------------------------------------------------------------------------
# UI control panel
# ---------------------------------------------------------------------------

def _build_control_panel(app_state, settings, session_state: dict) -> None:
    """
    Build the top control bar with buttons and settings controls.
    Uses Dear PyGui widgets — replaces pygame_gui entirely.
    session_state is a mutable dict used to signal restart/quit to the main loop.
    """
    sw = app_state.screen_width

    with dpg.window(
        tag="control_panel",
        no_title_bar=True,
        no_resize=True,
        no_move=True,
        no_scrollbar=True,
        no_collapse=True,
        pos=(0, 0),
        width=sw,
        height=55,
    ):
        # DPG 2.x: use group(horizontal=True) instead of deprecated add_same_line()
        with dpg.group(horizontal=True):
            dpg.add_button(
                label="RESTART",
                callback=lambda: session_state.update({"action": "restart"}),
                width=120, height=40,
            )
            dpg.add_button(
                label="RESET SCREEN",
                callback=lambda: session_state.update({"action": "reset"}),
                width=140, height=40,
            )
            dpg.add_spacer(width=20)

            # S2 — Trail selector (None / Medium / Long)
            dpg.add_text("Trail:", indent=0)
            trail_items = ["None", "Medium", "Long"]
            trail_map   = {"None": 0, "Medium": 30, "Long": 100}
            trail_rmap  = {0: "None", 30: "Medium", 100: "Long"}
            # Find closest label for current setting
            current_label = trail_rmap.get(settings.trail_length, "Long")
            dpg.add_combo(
                tag="trail_combo",
                items=trail_items,
                default_value=current_label,
                width=90,
                callback=lambda s, v: _on_trail_change(trail_map[v], settings),
            )
            dpg.add_spacer(width=20)

            # S3 — Zoom slider
            dpg.add_text("Zoom:")
            dpg.add_slider_float(
                tag="zoom_slider",
                default_value=settings.zoom_factor,
                min_value=0.1,
                max_value=10.0,
                width=140,
                format="%.2fx",
                callback=lambda s, v: _on_zoom_change(v, settings, app_state),
            )
            dpg.add_spacer(width=10)
            dpg.add_button(
                label="Auto-Scale",
                tag="zoom_to_bbox_btn",
                callback=lambda: session_state.update({"action": "zoom_to_bbox"}),
                width=120, height=40,
            )


def _on_trail_change(value: int, settings) -> None:
    settings.trail_length = value
    settings.save()


def _on_zoom_change(value: float, settings, app_state) -> None:
    settings.zoom_factor = value
    # Immediately rescale zoomed extents so bounding box updates on slider drag
    app_state.zoomed_max_x = app_state.raw_max_x * value
    app_state.zoomed_max_y = app_state.raw_max_y * value
    app_state.zoomed_min_x = app_state.raw_min_x * value
    app_state.zoomed_min_y = app_state.raw_min_y * value
    settings.save()


# ---------------------------------------------------------------------------
# Click handling — cursor toggle vs target circle
# ---------------------------------------------------------------------------

def _on_zoom_to_bbox(raw_max_x, raw_max_y, raw_min_x, raw_min_y, app_state, settings) -> None:
    bbox_w = max(abs(raw_max_x), abs(raw_min_x)) * 2
    bbox_h = max(abs(raw_max_y), abs(raw_min_y)) * 2
    base_w = app_state.screen_width  * 0.9
    base_h = app_state.screen_height * 0.9
    if bbox_w < 1 or bbox_h < 1:
        return
    new_zoom = round(min(base_w / bbox_w, base_h / bbox_h), 2)
    new_zoom = max(0.1, min(10.0, new_zoom))
    settings.zoom_factor = new_zoom
    dpg.set_value("zoom_slider", new_zoom)
    settings.save()


# Cached stats values — stats drawlist only redraws when these change.
# This eliminates the sub-pixel jitter that caused blurry text.
_stats_cache = {"left": -1, "weight": -1, "right": -1}


def _build_stats_bar(app_state) -> None:
    # Create or reuse a dedicated drawlist for stats (bar + text).
    # front=True ensures it draws above the canvas drawlist.
    if not dpg.does_item_exist("stats_dl"):
        dpg.add_viewport_drawlist(tag="stats_dl", front=True)
    # Clear any content from a previous session
    dpg.delete_item("stats_dl", children_only=True)
    # Reset cache to force a full redraw on first frame
    _stats_cache["left"]   = -1
    _stats_cache["weight"] = -1
    _stats_cache["right"]  = -1


def _update_stats_bar(perc_left: float, perc_right: float, curr_weight: float) -> None:
    left_val   = int(perc_left   * 100)
    weight_val = int(curr_weight)
    right_val  = int(perc_right  * 100)

    # Only redraw if values actually changed
    if (left_val   == _stats_cache["left"] and
        weight_val == _stats_cache["weight"] and
        right_val  == _stats_cache["right"]):
        return

    _stats_cache["left"]   = left_val
    _stats_cache["weight"] = weight_val
    _stats_cache["right"]  = right_val

    sw = dpg.get_viewport_width()
    vh = dpg.get_viewport_height()
    font_size = max(24, int(vh * 0.055))
    # Sit above the 20px weight bar with padding, using integer coords
    y = int(vh - font_size - 50)

    bar_top = vh - 50
    bar_bot = vh

    dpg.delete_item("stats_dl", children_only=True)

    # Weight distribution bar (red background, green for each side)
    dpg.draw_rectangle((0, bar_top), (sw, bar_bot),
                       fill=(255, 0, 0, 255), color=(255, 0, 0, 255), parent="stats_dl")
    if _stats_cache["weight"] > 0:
        pl = _stats_cache["left"]  / 100
        pr = _stats_cache["right"] / 100
    else:
        pl = pr = 0.5
    x0 = sw // 2 - pl * sw // 2
    dpg.draw_rectangle((x0, bar_top), (sw // 2, bar_bot),
                       fill=(0, 255, 0, 255), color=(0, 255, 0, 255), parent="stats_dl")
    x0 = sw // 2
    x1 = sw // 2 + pr * sw // 2
    dpg.draw_rectangle((x0, bar_top), (x1, bar_bot),
                       fill=(0, 255, 0, 255), color=(0, 255, 0, 255), parent="stats_dl")

    # Text above the bar
    dpg.draw_text((10,                  y), f"{left_val}%",     color=(0, 0, 0, 255), size=font_size, parent="stats_dl")
    dpg.draw_text((sw // 2 - 40,        y), f"{weight_val} kg", color=(0, 0, 0, 255), size=font_size, parent="stats_dl")
    dpg.draw_text((sw - font_size * 3,  y), f"{right_val}%",    color=(0, 0, 0, 255), size=font_size, parent="stats_dl")


def _handle_canvas_click(mx: float, my: float, app_state, settings) -> None:
    """
    Left click on canvas: toggle cursor mode if clicking on cursor,
    otherwise add a target circle.
    """
    cursor_radius = (int(0.05 * app_state.screen_height)
                     if settings.cursor_mode == "avatar" else 20)
    dist = math.sqrt((mx - app_state.ball_x) ** 2 + (my - app_state.ball_y) ** 2)
    if dist <= cursor_radius:
        settings.toggle_cursor_mode()
    else:
        app_state.clicked_locations.append((mx, my))


# ---------------------------------------------------------------------------
# Main run loop
# ---------------------------------------------------------------------------

def run(app_state, settings, args) -> None:
    """Outer loop — restarts session on RESTART, exits on QUIT."""
    while dpg.is_dearpygui_running():
        result = _run_session(app_state, settings, args)
        if result != 0:
            break


def _run_session(app_state, settings, args) -> int:
    """
    One full session: connect → tare → calibrate → main loop.
    Returns 0 to restart, 1 to quit.
    """
    app_state.reset()

    # Update screen dimensions from current viewport
    app_state.screen_width  = dpg.get_viewport_width()
    app_state.screen_height = dpg.get_viewport_height() - 55  # subtract control bar

    ensure_textures_loaded()

    # viewport_drawlist draws directly onto the viewport background (full screen)
    dl = dpg.add_viewport_drawlist(front=False)

    session_state = {"action": None}

    # Clean up any previous control panel
    if dpg.does_item_exist("control_panel"):
        dpg.delete_item("control_panel")

    _build_control_panel(app_state, settings, session_state)

    _build_stats_bar(app_state)

    # Register canvas click handler via a handler registry
    if dpg.does_item_exist("click_handler"):
        dpg.delete_item("click_handler")
    with dpg.handler_registry(tag="click_handler"):
        dpg.add_mouse_click_handler(
            button=0,
            callback=lambda: _handle_canvas_click(
                *dpg.get_mouse_pos(local=False), app_state, settings
            ),
        )

    # --- Step 1: Connect ---
    try:
        connected = _try_connection_loop(dl, app_state, use_mock=args.mock)
        if not connected:
            return 1
    except Exception as e:
        print(f"Connection failed: {e}")
        return 1

    device = connect_wii_board(use_mock=args.mock, mock_scenario=args.mock_scenario)
    if not device:
        return 1

    # Show connecting screen while taring
    dpg.delete_item(dl, children_only=True)
    draw_connection_screen(dl, app_state)
    dpg.render_dearpygui_frame()

    # --- Step 2: Tare ---
    wait_for_tare(device, dl, app_state)
    try:
        tare(device, app_state.data_struct)
    except Exception as e:
        print(f"Failed to tare: {e}")
        device.close()
        return 1

    # --- Step 3: Calibration ---
    on_start = device.trigger_step_on if hasattr(device, "trigger_step_on") else None
    calibrated_weight = sensitivity_calibration(device, dl, app_state, on_start=on_start)
    if calibrated_weight == -1:
        return 1
    app_state.weight = calibrated_weight

    # --- Step 4: Main loop ---
    # Extents now stored in app_state so zoom callback can rescale them live.
    # app_state.reset() already zeroes these — nothing else needed here.
    app_state.zoomed_max_x = app_state.zoomed_max_y = 0.0
    app_state.zoomed_min_x = app_state.zoomed_min_y = 0.0

    while dpg.is_dearpygui_running():

        # Handle control panel actions
        action = session_state.get("action")
        if action == "restart":
            device.close()
            dpg.delete_item(dl)
            return 0
        if action == "reset":
            app_state.clicked_locations = []
            app_state.historical_coords = [(0, 0)] * settings.trail_length
            app_state.zoomed_max_x = app_state.zoomed_max_y = 0.0
            app_state.zoomed_min_x = app_state.zoomed_min_y = 0.0
            app_state.raw_max_x = app_state.raw_max_y = 0.0
            app_state.raw_min_x = app_state.raw_min_y = 0.0
            session_state["action"] = None
        if action == "zoom_to_bbox":
            _on_zoom_to_bbox(app_state.raw_max_x, app_state.raw_max_y,
                             app_state.raw_min_x, app_state.raw_min_y,
                             app_state, settings)
            app_state.zoomed_max_x = app_state.raw_max_x * settings.zoom_factor
            app_state.zoomed_max_y = app_state.raw_max_y * settings.zoom_factor
            app_state.zoomed_min_x = app_state.raw_min_x * settings.zoom_factor
            app_state.zoomed_min_y = app_state.raw_min_y * settings.zoom_factor
            session_state["action"] = None

        # Handle viewport resize
        vw = dpg.get_viewport_width()
        vh = dpg.get_viewport_height() - 55
        if vw != app_state.screen_width or vh != app_state.screen_height:
            app_state.screen_width  = vw
            app_state.screen_height = vh
            dpg.configure_item("control_panel", width=vw)
            # stats_dl redraws itself at correct position on next value change

        # Read sensor data
        data = read_data(device)
        if data:
            corners = parse_data(data, app_state.data_struct)
            top_right, bottom_right, top_left, bottom_left = corners.values()

            # Raw coords (zoom=1.0) — stored for zoom-to-bbox calculation
            raw_x, raw_y = calculate_coordinates(
                top_left, top_right, bottom_left, bottom_right,
                weight=app_state.weight,
                screen_width=app_state.screen_width,
                screen_height=app_state.screen_height,
                zoom=1.0,
            )
            app_state.raw_max_x = max(app_state.raw_max_x, raw_x)
            app_state.raw_max_y = max(app_state.raw_max_y, raw_y)
            app_state.raw_min_x = min(app_state.raw_min_x, raw_x)
            app_state.raw_min_y = min(app_state.raw_min_y, raw_y)

            # Zoomed coords derived from raw — always correct after zoom change
            x = raw_x * settings.zoom_factor
            y = raw_y * settings.zoom_factor
            app_state.zoomed_max_x = max(app_state.zoomed_max_x, x)
            app_state.zoomed_max_y = max(app_state.zoomed_max_y, y)
            app_state.zoomed_min_x = min(app_state.zoomed_min_x, x)
            app_state.zoomed_min_y = min(app_state.zoomed_min_y, y)

            ball_x = int(app_state.screen_width  // 2 + x)
            # ball_y is in full viewport coords: canvas centre is at (screen_height/2 + 55)
            # where 55 is the control bar height. screen_height already excludes the bar,
            # so the canvas centre in viewport space is screen_height//2 + 55.
            ball_y = int(app_state.screen_height // 2 + y + 55)

            app_state.ball_x = ball_x
            app_state.ball_y = ball_y

            app_state.historical_coords.append((ball_x, ball_y))
            if len(app_state.historical_coords) > settings.trail_length:
                app_state.historical_coords.pop(0)

            curr_weight = sum(corners.values())

            # Redraw canvas
            dpg.delete_item(dl, children_only=True)
            draw_main_screen(
                dl=dl,
                corners=corners,
                ball_x=ball_x,
                ball_y=ball_y,
                curr_weight=curr_weight,
                max_x=app_state.zoomed_max_x, max_y=app_state.zoomed_max_y,
                min_x=app_state.zoomed_min_x, min_y=app_state.zoomed_min_y,
                app_state=app_state,
                settings=settings,
            )
            # Update crisp stats bar (avoids blurry drawlist text)
            if app_state.weight > 0:
                pl = (corners["top_left"]  + corners["bottom_left"])  / app_state.weight
                pr = (corners["top_right"] + corners["bottom_right"]) / app_state.weight
            else:
                pl = pr = 0.5
            _update_stats_bar(pl, pr, curr_weight)

        dpg.render_dearpygui_frame()

    device.close()
    return 1