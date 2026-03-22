# app.py
import pygame
import pygame_gui
import hid
from board_connection import try_connection

from constants       import VENDOR_ID, PRODUCT_ID, DLL_RELATIVE_PATH
from resources       import ICON_PATH, PERSON_IMAGE_PATH, CONNECTION_PATH, resource_path
from data_processing import read_data, parse_data, tare, calculate_coordinates
from calibration     import wait_for_tare, sensitivity_calibration
from ui              import draw_main_screen, show_connection_failed, display_message
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


def _wait_for_key():
    """Block until Enter is pressed or the window is closed."""
    while True:
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                return
            if event.type == pygame.QUIT:
                pygame.quit()
                return -1


def try_connection_loop(screen, app_state, use_mock: bool = False) -> None:
    """Show connection screen and loop until board connects (skipped in mock)."""
    if use_mock:
        print("[MOCK] Skipping connection screen.")
        return

    font       = pygame.font.Font(None, 82)
    mid_screen = app_state.screen_width  / 2.5
    mid_height = app_state.screen_height / 2.9

    while True:
        screen.fill((110, 159, 168))
        display_message(screen, font, "Trying to connect", (250, 250, 250), (mid_screen, mid_height))
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return

        result = try_connection(resource_path(DLL_RELATIVE_PATH))
        if result == 0:
            break
        elif result == 1:
            show_connection_failed(screen, font, app_state)
            _wait_for_key()


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def run(app_state, settings, args) -> None:
    """
    Outer run loop — re-enters main() on RESTART, exits on QUIT or error.
    """
    while True:
        result = _run_session(app_state, settings, args)
        if result != 0:
            break
        # result == 0 means RESTART was pressed — loop again


def _run_session(app_state, settings, args) -> int:
    """
    One full session: connect → tare → calibrate → main loop.
    Returns 0 to restart, 1 to quit.
    """
    app_state.reset()

    # --- pygame display setup ---
    screen = pygame.display.set_mode(
        (int(app_state.screen_width), int(app_state.screen_height)),
        pygame.RESIZABLE,
    )
    pygame.display.set_caption("WIIBBLE - Wii Balance Board Live Environment")
    pygame.display.set_icon(pygame.image.load(ICON_PATH))

    manager = pygame_gui.UIManager((app_state.screen_width, app_state.screen_height))
    restart_btn = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((0, 0), (150, 50)),
        text="RESTART",
        manager=manager,
        object_id="#restart_button",
    )
    reset_btn = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((150, 0), (150, 50)),
        text="RESET SCREEN",
        manager=manager,
        object_id="#reset_button",
    )
    clock = pygame.time.Clock()

    # --- Step 1: Connect ---
    try:
        try_connection_loop(screen, app_state, use_mock=args.mock)
    except Exception as e:
        print(f"Connection failed: {e}")
        return 1

    device = connect_wii_board(use_mock=args.mock, mock_scenario=args.mock_scenario)
    if not device:
        return 1

    # --- Step 2: Tare (board empty) ---
    wait_for_tare(device, screen, app_state)
    try:
        tare(device, app_state.data_struct)
    except Exception as e:
        print(f"Failed to tare: {e}")
        device.close()
        return 1

    # --- Step 3: Sensitivity calibration (step on board) ---
    # on_start switches mock to body-weight phase AFTER baseline is measured
    on_start = device.trigger_step_on if hasattr(device, "trigger_step_on") else None
    calibrated_weight = sensitivity_calibration(device, screen, app_state, on_start=on_start)
    if calibrated_weight == -1:
        return 1
    app_state.weight = calibrated_weight

    # --- Step 4: Main loop ---
    max_x = max_y = 0
    min_x, min_y = app_state.screen_width, app_state.screen_height
    person_image = pygame.image.load(PERSON_IMAGE_PATH)

    try:
        while True:
            time_delta = clock.tick(60) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    device.close()
                    return 1

                elif event.type == pygame.VIDEORESIZE:
                    app_state.screen_width  = event.w
                    app_state.screen_height = event.h
                    screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)

                elif event.type == pygame_gui.UI_BUTTON_PRESSED:
                    if event.ui_element == restart_btn:
                        device.close()
                        return 0   # signal outer loop to restart
                    if event.ui_element == reset_btn:
                        app_state.clicked_locations = []
                        app_state.historical_coords = [(0, 0)] * settings.trail_length
                        max_x = max_y = 0
                        min_x, min_y = app_state.screen_width, app_state.screen_height

                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    app_state.clicked_locations.append(event.pos)

                manager.process_events(event)

            data = read_data(device)
            if data:
                corners = parse_data(data, app_state.data_struct)
                top_right, bottom_right, top_left, bottom_left = corners.values()

                x, y = calculate_coordinates(
                    top_left, top_right, bottom_left, bottom_right,
                    weight=app_state.weight,
                    screen_width=app_state.screen_width,
                    screen_height=app_state.screen_height,
                    zoom=settings.zoom_factor,
                )

                max_x, max_y = max(max_x, x), max(max_y, y)
                min_x, min_y = min(min_x, x), min(min_y, y)

                ball_x = int(app_state.screen_width  // 2 + x)
                ball_y = int(app_state.screen_height // 2 + y)

                app_state.historical_coords.append((ball_x, ball_y))
                # Keep list capped at trail_length (S2)
                if len(app_state.historical_coords) > settings.trail_length:
                    app_state.historical_coords.pop(0)

                curr_weight = sum(corners.values())

                draw_main_screen(
                    screen=screen,
                    corners=corners,
                    ball_x=ball_x,
                    ball_y=ball_y,
                    curr_weight=curr_weight,
                    max_x=max_x, max_y=max_y,
                    min_x=min_x, min_y=min_y,
                    person_image=person_image,
                    app_state=app_state,
                    settings=settings,
                )

            manager.update(time_delta)
            manager.draw_ui(screen)
            pygame.display.flip()

    except KeyboardInterrupt:
        print("Interrupted.")
        device.close()
        return 1