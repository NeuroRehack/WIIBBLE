# app.py
import math
import dearpygui.dearpygui as dpg
import hid
import time
import os, csv, datetime

from board_connection import try_connection

from constants       import (VENDOR_ID, PRODUCT_ID, DLL_RELATIVE_PATH,
                              ZOOM_MIN, ZOOM_MAX, FILTER_MIN, FILTER_MAX, COORD_SCALE, ZOOM_SCALE)
from resources       import ICON_PATH, resource_path
from data_processing import read_data, parse_data, tare, calculate_coordinates, apply_filter, calculate_force_deviation_kg
from calibration     import wait_for_tare, sensitivity_calibration
from ui              import (draw_main_screen, draw_connection_screen,
                             draw_connection_failed_screen, ensure_textures_loaded,
                             STATS_STRIP_H, STATS_FONT_SCALE, STATS_FONT_MIN)
import theme as _theme_module
from theme           import (BAR_BG_COLOR, BAR_LEFT_COLOR, BAR_RIGHT_COLOR, STATS_TEXT_COLOR,
                              ICON_COG)
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

# ---------------------------------------------------------------------------
# UI layout constants — all widget sizes in one place
# ---------------------------------------------------------------------------
TOOLBAR_FULL_H      = 55    # toolbar window height in pixels
GEAR_BTN_SIZE       = 40    # gear toggle button width and height
TOOLBAR_BTN_H       = 40    # standard toolbar button height
TOOLBAR_BTN_W_SM    = 110   # small button width (RESTART, Auto-Scale)
TOOLBAR_BTN_W_MD    = 130   # medium button width (RESET SCREEN)
TOOLBAR_SLIDER_W    = 140   # slider width (zoom, filter)
TOOLBAR_COMBO_W     = 90    # combo box width (trail)
TOOLBAR_SPACER_SM   = 8     # small spacer between related items
TOOLBAR_SPACER_MD   = 16    # medium spacer between groups

# Click detection radii
CURSOR_HIT_RADIUS_CIRCLE = 20   # px — circle cursor click detection radius
CURSOR_HIT_FRACTION      = 0.05 # fraction of screen height for avatar cursor

def _get_gear_label() -> str:
    # Access FA_ICON_FONT via module to get the live value, not the import-time None
    return ICON_COG if _theme_module.FA_ICON_FONT is not None else "[=]"


def _toggle_toolbar(session_state: dict) -> None:
    visible = not session_state.get("toolbar_visible", False)
    session_state["toolbar_visible"] = visible
    if visible:
        # Show full toolbar, hide floating gear
        if dpg.does_item_exist("control_panel"):
            dpg.configure_item("control_panel", show=True)
        if dpg.does_item_exist("gear_btn_window"):
            dpg.configure_item("gear_btn_window", show=False)
    else:
        # Hide full toolbar, show floating gear
        if dpg.does_item_exist("control_panel"):
            dpg.configure_item("control_panel", show=False)
        if dpg.does_item_exist("gear_btn_window"):
            dpg.configure_item("gear_btn_window", show=True)
    session_state["action"] = "toolbar_toggled"

# --- Cursor toggle helpers (top-level) ---
def _cursor_label(settings):
    return f"Cursor: {'Avatar' if settings.cursor_mode == 'avatar' else 'Circle'}"

def update_cursor_toggle_label(settings):
    import dearpygui.dearpygui as dpg
    dpg.set_item_label("cursor_toggle_btn", _cursor_label(settings))

def _on_cursor_toggle(settings):
    settings.toggle_cursor_mode()
    update_cursor_toggle_label(settings)
    
def _on_record_duration_change(value: int, settings, app_state) -> None:
    settings.record_duration = value
    app_state.record_duration = value
    settings.save()

def _on_start_recording(app_state, settings) -> None:
    if app_state.is_recording or app_state.is_countdown:
        return  # Prevent double start
    app_state.is_countdown = True
    app_state.countdown_value = 4
    app_state.record_duration = settings.record_duration
    app_state.record_buffer = []
    app_state.recording_indicator = False

def _build_control_panel(app_state, settings, session_state: dict) -> None:
    """
    Builds two windows that are mutually exclusive:

    control_panel     — full opaque toolbar (expanded state)
    gear_btn_window   — tiny no_background floating button (collapsed state)

    Canvas always fills full viewport. Toolbar windows float on top.
    """
    sw = app_state.screen_width

    # --- Full toolbar ---
    with dpg.window(
        tag="control_panel",
        no_title_bar=True, no_resize=True, no_move=True,
        no_scrollbar=True, no_collapse=True,
        pos=(0, 0), width=sw, height=TOOLBAR_FULL_H, show=False,
    ):
        with dpg.group(horizontal=True):
            dpg.add_button(
                tag="toggle_btn", label=_get_gear_label(),
                callback=lambda: _toggle_toolbar(session_state),
                width=GEAR_BTN_SIZE, height=GEAR_BTN_SIZE,
            )
            dpg.add_spacer(width=8)
            with dpg.group(tag="settings_group", horizontal=True):
                dpg.add_button(
                    label="RESTART",
                    callback=lambda: session_state.update({"action": "restart"}),
                    width=TOOLBAR_BTN_W_SM, height=TOOLBAR_BTN_H,
                )
                dpg.add_button(
                    label="RESET SCREEN",
                    callback=lambda: session_state.update({"action": "reset"}),
                    width=TOOLBAR_BTN_W_MD, height=TOOLBAR_BTN_H,
                )
                dpg.add_spacer(width=TOOLBAR_SPACER_MD)
                # --- S5: Recording duration input and Start Recording button ---
                dpg.add_text("Record Duration (s):")
                dpg.add_input_int(
                    tag="record_duration_input",
                    default_value=int(settings.record_duration),
                    min_value=1, max_value=120, width=80,
                    callback=lambda s, v: _on_record_duration_change(v, settings, app_state),
                )
                dpg.add_spacer(width=TOOLBAR_SPACER_SM)
                dpg.add_button(
                    tag="start_recording_btn",
                    label="Start Recording",
                    width=TOOLBAR_BTN_W_SM, height=TOOLBAR_BTN_H,
                    callback=lambda: _on_start_recording(app_state, settings),
                    enabled=not app_state.is_recording and not app_state.is_countdown,
                )

                # --- Cursor toggle button ---
                dpg.add_button(
                    tag="cursor_toggle_btn",
                    label=_cursor_label(settings),
                    callback=lambda: _on_cursor_toggle(settings),
                    width=TOOLBAR_BTN_W_SM, height=TOOLBAR_BTN_H,
                )
                # Expose label update function for use elsewhere
                app_state.update_cursor_toggle_label = lambda: update_cursor_toggle_label(settings)
                dpg.add_spacer(width=TOOLBAR_SPACER_MD)
                dpg.add_text("Trail:")
                trail_items   = ["None", "Medium", "Long"]
                trail_map     = {"None": 0, "Medium": 30, "Long": 100}
                trail_rmap    = {0: "None", 30: "Medium", 100: "Long"}
                current_label = trail_rmap.get(settings.trail_length, "Long")
                dpg.add_combo(
                    tag="trail_combo", items=trail_items,
                    default_value=current_label, width=TOOLBAR_COMBO_W,
                    callback=lambda s, v: _on_trail_change(trail_map[v], settings),
                )
                dpg.add_spacer(width=TOOLBAR_SPACER_MD)
                dpg.add_text("Filter:")
                dpg.add_slider_int(
                    tag="filter_slider",
                    default_value=settings.filter_window,
                    min_value=FILTER_MIN, max_value=FILTER_MAX,
                    width=TOOLBAR_SLIDER_W,
                    format="%d frames",
                    callback=lambda s, v: _on_filter_change(v, settings, app_state),
                )
                dpg.add_spacer(width=TOOLBAR_SPACER_MD)
                dpg.add_text("Zoom:")
                dpg.add_slider_float(
                    tag="zoom_slider",
                    default_value=settings.zoom_factor,
                    min_value=ZOOM_MIN, max_value=ZOOM_MAX,
                    width=TOOLBAR_SLIDER_W,
                    format="%.2fx",
                    callback=lambda s, v: _on_zoom_change(v, settings, app_state),
                )
                dpg.add_spacer(width=TOOLBAR_SPACER_SM)
                dpg.add_button(
                    label="Auto-Scale", tag="zoom_to_bbox_btn",
                    callback=lambda: session_state.update({"action": "zoom_to_bbox"}),
                    width=TOOLBAR_BTN_W_SM, height=TOOLBAR_BTN_H,
                )    # --- Floating gear button (collapsed state) ---
    # no_background=True means zero DPG chrome — just the button pixel-perfect
    if dpg.does_item_exist("gear_btn_window"):
        dpg.delete_item("gear_btn_window")
    with dpg.window(
        tag="gear_btn_window",
        no_title_bar=True, no_resize=True, no_move=True,
        no_scrollbar=True, no_collapse=True,
        no_background=True,
        pos=(4, 4),
        width=GEAR_BTN_SIZE + 4, height=GEAR_BTN_SIZE + 4,
        show=True,
    ):
        dpg.add_button(
            tag="gear_float_btn", label=_get_gear_label(),
            callback=lambda: _toggle_toolbar(session_state),
            width=GEAR_BTN_SIZE, height=GEAR_BTN_SIZE,
        )

    # Bind icon font to gear buttons if FontAwesome loaded successfully
    if _theme_module.FA_ICON_FONT is not None:
        dpg.bind_item_font("toggle_btn",     _theme_module.FA_ICON_FONT)
        dpg.bind_item_font("gear_float_btn", _theme_module.FA_ICON_FONT)


def _on_trail_change(value: int, settings) -> None:
    settings.trail_length = value
    settings.save()


def _on_filter_change(value: int, settings, app_state) -> None:
    settings.filter_window = value
    # Trim buffer immediately if window shrank
    if len(app_state.filter_buffer) > value:
        app_state.filter_buffer = app_state.filter_buffer[-value:]
    settings.save()


def _on_zoom_change(value: float, settings, app_state) -> None:
    value = ZOOM_SCALE**value
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
    base_w = app_state.screen_width  * COORD_SCALE
    base_h = app_state.screen_height * COORD_SCALE
    if bbox_w < 1 or bbox_h < 1:
        return
    new_zoom = round(min(base_w / bbox_w, base_h / bbox_h), 10)
    new_zoom = max(ZOOM_MIN, min(ZOOM_MAX, new_zoom))
    settings.zoom_factor = new_zoom
    new_zoom = math.log(new_zoom)/math.log(ZOOM_SCALE)  # convert back to slider value
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
    font_size = max(STATS_FONT_MIN, int(vh * STATS_FONT_SCALE))
    bar_top   = vh - STATS_STRIP_H
    bar_bot   = vh
    y         = bar_top - font_size - 6

    dpg.delete_item("stats_dl", children_only=True)

    # Weight distribution bar — muted teal palette (from theme.py)
    dpg.draw_rectangle((0, bar_top), (sw, bar_bot),
                       fill=BAR_BG_COLOR, color=BAR_BG_COLOR, parent="stats_dl")
    if _stats_cache["weight"] > 0:
        pl = _stats_cache["left"]  / 100
        pr = _stats_cache["right"] / 100
    else:
        pl = pr = 0.5
    x0 = sw // 2 - pl * sw // 2
    dpg.draw_rectangle((x0, bar_top), (sw // 2, bar_bot),
                       fill=BAR_LEFT_COLOR, color=BAR_LEFT_COLOR, parent="stats_dl")
    x0 = sw // 2
    x1 = sw // 2 + pr * sw // 2
    dpg.draw_rectangle((x0, bar_top), (x1, bar_bot),
                       fill=BAR_RIGHT_COLOR, color=BAR_RIGHT_COLOR, parent="stats_dl")

    # Text above the bar
    dpg.draw_text((10,                  y), f"{left_val}%",     color=STATS_TEXT_COLOR, size=font_size, parent="stats_dl")
    dpg.draw_text((sw // 2 - 40,        y), f"{weight_val} kg", color=STATS_TEXT_COLOR, size=font_size, parent="stats_dl")
    dpg.draw_text((sw - font_size * 3,  y), f"{right_val}%",    color=STATS_TEXT_COLOR, size=font_size, parent="stats_dl")


def _handle_canvas_click(mx: float, my: float, app_state, settings) -> None:
    """
    Left click on canvas: toggle cursor mode if clicking on cursor,
    otherwise add a target circle.
    Ignores clicks in the toolbar area.
    """
    if my <= TOOLBAR_FULL_H:
        return
    cursor_radius = (int(CURSOR_HIT_FRACTION * app_state.screen_height)
                     if settings.cursor_mode == "avatar" else CURSOR_HIT_RADIUS_CIRCLE)
    dist = math.sqrt((mx - app_state.ball_x) ** 2 + (my - app_state.ball_y) ** 2)
    if dist <= cursor_radius:
        settings.toggle_cursor_mode()
        # Update toolbar button label if function is available
        if hasattr(app_state, "update_cursor_toggle_label"):
            app_state.update_cursor_toggle_label()
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

def _save_recording_csv(record_buffer):
    out_dir = os.path.join(os.getcwd(), "recordings")
    os.makedirs(out_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"recording_{timestamp}.csv"
    path = os.path.join(out_dir, filename)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["time (s)", "x (kg)", "y (kg)"])
        for row in record_buffer:
            writer.writerow([f"{row[0]:.3f}", f"{row[1]:.3f}", f"{row[2]:.3f}"])
    print(f"[Recording] Saved to {path}")

def _run_session(app_state, settings, args) -> int:
    """
    One full session: connect → tare → calibrate → main loop.
    Returns 0 to restart, 1 to quit.
    """
    app_state.reset()

    # Update screen dimensions from current viewport
    app_state.screen_width  = dpg.get_viewport_width()
    # During connect/tare/calibration toolbar is hidden — use full height.
    # After calibration it shows, and resize handler corrects screen_height.
    app_state.screen_height = dpg.get_viewport_height()

    ensure_textures_loaded()

    # viewport_drawlist draws directly onto the viewport background (full screen)
    dl = dpg.add_viewport_drawlist(front=False)

    session_state = {"action": None, "toolbar_visible": False}

    # Clean up previous session widgets
    for _tag in ("control_panel", "gear_btn_window"):
        if dpg.does_item_exist(_tag):
            dpg.delete_item(_tag)

    _build_control_panel(app_state, settings, session_state)
    # Show only the floating gear button (collapsed toolbar) at startup
    dpg.configure_item("control_panel", show=False)
    if dpg.does_item_exist("gear_btn_window"):
        dpg.configure_item("gear_btn_window", show=True)

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


    last_countdown_tick = time.time()
    record_start_time = None
    while dpg.is_dearpygui_running():
        # --- S5: Countdown and Recording Logic ---
        now = time.time()
        # Countdown phase
        if app_state.is_countdown:
            if now - last_countdown_tick >= 1.0:
                app_state.countdown_value -= 1
                last_countdown_tick = now
                if app_state.countdown_value <= 0:
                    app_state.is_countdown = False
                    app_state.is_recording = True
                    app_state.recording_indicator = True
                    record_start_time = now
                    app_state.record_start = now
                    app_state.record_buffer = []
        # Recording phase
        if app_state.is_recording:
            elapsed = now - (record_start_time if record_start_time else app_state.record_start)
            # Get x, y in kg for CSV
            x_kg, y_kg = calculate_force_deviation_kg(top_left, top_right, bottom_left, bottom_right)
            # Timestamp is relative to recording start
            app_state.record_buffer.append((elapsed, x_kg, y_kg))
            # Cap at 100 Hz (skip frames if running faster)
            if elapsed >= app_state.record_duration:
                app_state.is_recording = False
                app_state.recording_indicator = False
                # Save CSV file
                _save_recording_csv(app_state.record_buffer)
        # Visual feedback overlays are now drawn in ui.draw_main_screen



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

        # Toolbar toggle — just consume, canvas never resizes
        if action == "toolbar_toggled":
            session_state["action"] = None

        # Canvas is always viewport_height - TOOLBAR_FULL_H.
        # Toolbar floats over canvas — toggling it never changes screen dimensions.
        vw = dpg.get_viewport_width()
        vh = dpg.get_viewport_height()
        if vw != app_state.screen_width or vh != app_state.screen_height:
            app_state.screen_width  = vw
            app_state.screen_height = vh
            dpg.configure_item("control_panel", width=vw*0.85, show=False)  # Resize toolbar to new width, keep it hidden until toggle
            # stats_dl redraws itself at correct position on next value change

        # Read sensor data
        data = read_data(device)
        if data:
            corners = parse_data(data, app_state.data_struct)

            # S4 — Moving average filter (see data_processing.apply_filter)
            smoothed = apply_filter(
                corners, app_state.filter_buffer, settings.filter_window
            )
            top_right    = smoothed["top_right"]
            bottom_right = smoothed["bottom_right"]
            top_left     = smoothed["top_left"]
            bottom_left  = smoothed["bottom_left"]

            # Raw coords (zoom=1.0) — derived from smoothed sensor values
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

            # Zoomed coords
            x = raw_x * settings.zoom_factor
            y = raw_y * settings.zoom_factor
            app_state.zoomed_max_x = max(app_state.zoomed_max_x, x)
            app_state.zoomed_max_y = max(app_state.zoomed_max_y, y)
            app_state.zoomed_min_x = min(app_state.zoomed_min_x, x)
            app_state.zoomed_min_y = min(app_state.zoomed_min_y, y)

            ball_x = int(app_state.screen_width  // 2 + x)
            # ball_y: canvas centre is screen_height/2, no toolbar offset
            ball_y = int(app_state.screen_height // 2 + y)

            app_state.ball_x = ball_x
            app_state.ball_y = ball_y

            app_state.historical_coords.append((ball_x, ball_y))
            if len(app_state.historical_coords) > settings.trail_length:
                app_state.historical_coords.pop(0)

            curr_weight = sum(smoothed.values())

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
                pl = (smoothed["top_left"]  + smoothed["bottom_left"])  / app_state.weight
                pr = (smoothed["top_right"] + smoothed["bottom_right"]) / app_state.weight
            else:
                pl = pr = 0.5
            _update_stats_bar(pl, pr, curr_weight)

        dpg.render_dearpygui_frame()

    device.close()
    return 1