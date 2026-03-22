# ui.py
import pygame
import numpy as np
from resources import IMAGE_PATHS, CONNECTION_PATH


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def display_message(screen, font, message: str, color, position):
    """
    Render a (possibly multi-line) string onto screen.
    Blank lines advance the y position by one line height.
    """
    lines = message.split('\n')
    y_offset = 0
    for line in lines:
        if line.strip() == '':
            y_offset += font.get_linesize()
            continue
        text = font.render(line, True, color)
        screen.blit(text, (position[0], position[1] + y_offset))
        y_offset += font.get_linesize()


def _scale_image(image, screen_height: float):
    """Scale an image to 80% of screen height, preserving aspect ratio."""
    w, h = image.get_size()
    new_w = int(0.8 * screen_height * w / h)
    new_h = int(0.8 * screen_height)
    return pygame.transform.scale(image, (new_w, new_h))


# ---------------------------------------------------------------------------
# Calibration screens
# ---------------------------------------------------------------------------

def show_step_instruction(screen, image, step: str, app_state) -> None:
    """
    Show the 'Step ON' or 'Step OFF' instruction screen.
    step: "on" | "off"
    Replaces the near-identical show_step_on_board / show_step_off_board pair.
    """
    sw, sh = app_state.screen_width, app_state.screen_height
    mid_screen = sw / 1.8
    mid_height = sh / 2.9
    font = pygame.font.Font(None, 82)

    screen.fill((110, 159, 168))
    scaled = _scale_image(image, sh)
    iw, ih = scaled.get_size()
    screen.blit(scaled, (sw // 2.2 - iw // 2, sh // 1.5 - ih // 2))

    display_message(screen, font, "         Step", (250, 250, 250), (mid_screen, mid_height))
    if step == "on":
        display_message(screen, font, "\n          ON",  (0, 250, 0),     (mid_screen, mid_height))
        display_message(screen, font, "\n\n     the board",           (250, 250, 250), (mid_screen, mid_height))
        display_message(screen, font, "\n\n\n\n\n\n and stand still", (250, 250, 250), (mid_screen, mid_height))
    else:
        display_message(screen, font, "\n         OFF",  (250, 0, 0),     (mid_screen, mid_height))
        display_message(screen, font, "\n\n     the board",           (250, 250, 250), (mid_screen, mid_height))

    pygame.display.flip()


def show_connection_failed(screen, font, app_state) -> None:
    """Render the 'Failed to connect' screen with checklist."""
    sw, sh = app_state.screen_width, app_state.screen_height
    mid_screen = sw / 2.5
    mid_height = sh / 2.9

    screen.fill((110, 159, 168))
    image = pygame.image.load(CONNECTION_PATH)
    scaled = _scale_image(image, sh)
    iw, ih = scaled.get_size()
    screen.blit(scaled, (sw // 2 - iw // 2, sh // 2 - ih // 2))

    display_message(screen, font, "Failed to connect",                                   (250, 0, 0),     (mid_screen * 0.6, mid_height))
    display_message(screen, font, "\nCheck the following: ",                             (250, 250, 250), (mid_screen * 0.6, mid_height))
    display_message(screen, font, "\n\n    1. bluetooth is enabled on your computer",   (250, 250, 250), (mid_screen * 0.6, mid_height))
    display_message(screen, font, "\n\n\n    2. the board is paired to your computer",  (250, 250, 250), (mid_screen * 0.6, mid_height))
    display_message(screen, font, "\n\n\n\n    3. the board is on and blinking blue",   (250, 250, 250), (mid_screen * 0.6, mid_height))
    display_message(screen, font, "\n\n\n\n\nand press enter",                          (250, 250, 250), (mid_screen * 0.6, mid_height))
    pygame.display.flip()


# ---------------------------------------------------------------------------
# Main loop rendering
# ---------------------------------------------------------------------------

def draw_main_screen(
    screen,
    corners: dict,
    ball_x: int,
    ball_y: int,
    curr_weight: float,
    max_x, max_y, min_x, min_y,
    person_image,
    app_state,
    settings,
) -> None:
    """
    Render one frame of the main balance display.

    Reads from app_state: screen dimensions, historical_coords, clicked_locations, weight.
    Reads from settings:  trail_length (S2), cursor_mode (S1).
    """
    sw, sh = app_state.screen_width, app_state.screen_height
    top_right    = corners["top_right"]
    bottom_right = corners["bottom_right"]
    top_left     = corners["top_left"]
    bottom_left  = corners["bottom_left"]

    screen.fill((255, 255, 255))

    # --- Centre lines ---
    line_w = max(1, int(sw / 200))
    pygame.draw.line(screen, (0, 0, 0), (0, sh // 2),   (sw, sh // 2),   line_w)
    pygame.draw.line(screen, (0, 0, 0), (sw // 2, 0),   (sw // 2, sh),   line_w)
    pygame.draw.circle(screen, (0, 0, 0),     (sw // 2, sh // 2), int(sw / 50))
    pygame.draw.circle(screen, (255, 255, 255),(sw // 2, sh // 2), int(sw / 20))

    # --- Clicked target circles ---
    for loc in app_state.clicked_locations:
        hit = np.linalg.norm(np.array(loc) - np.array([ball_x, ball_y])) < 50
        pygame.draw.circle(screen, (0, 255, 0) if hit else (255, 0, 0), loc, 50)

    # --- Trail (S2: respect settings.trail_length) ---
    trail_color = (110, 159, 168)
    coords = app_state.historical_coords[-settings.trail_length:]
    n = len(coords)
    for i in range(1, n):
        frac = i / n
        pygame.draw.circle(screen, (int(frac * 255), 0, 0),
                           coords[i], int(i * 20 / n))
        pygame.draw.circle(screen,
                           (int(frac * trail_color[0]),
                            int(frac * trail_color[1]),
                            int(frac * trail_color[2])),
                           coords[i], int(i * 20 / n))

    # --- Cursor (avatar or simple circle) ---
    # Both cursor types are clickable to toggle mode — the hit radius
    # matches what app.py uses for click detection.
    if settings.cursor_mode == "avatar":
        iw, ih = person_image.get_size()
        scaled = pygame.transform.scale(
            person_image,
            (int(0.1 * sh * iw / ih), int(0.1 * sh))
        )
        sw2, sh2 = scaled.get_size()
        screen.blit(scaled, (ball_x - sw2 // 2, ball_y - sh2))
    else:
        # Circle cursor: filled with outline so it reads as interactive
        pygame.draw.circle(screen, (110, 159, 168), (ball_x, ball_y), 20)

    # --- Bounding box of historical movement ---
    pygame.draw.rect(screen, (0, 0, 0),
                     (min_x + sw // 2, min_y + sh // 2,
                      max_x - min_x,   max_y - min_y),
                     line_w)

    # --- Weight distribution bar ---
    if app_state.weight > 0:
        perc_left  = (top_left  + bottom_left)  / app_state.weight
        perc_right = (top_right + bottom_right) / app_state.weight
    else:
        perc_left = perc_right = 0.5

    pygame.draw.rect(screen, (255, 0, 0), (0, sh - 20, int(sw), 20))
    x0 = sw // 2 - perc_left  * sw // 2
    x1 = sw // 2 - x0
    pygame.draw.rect(screen, (0, 255, 0), (x0, sh - 20, x1, 20))
    x0 = sw // 2
    x1 = perc_right * sw // 2
    pygame.draw.rect(screen, (0, 255, 0), (x0, sh - 20, x1, 20))

    # --- Text overlays ---
    font = pygame.font.Font(None, 64)
    screen.blit(font.render(f"{int(perc_left  * 100)}%", True, (0, 0, 0)), (50,       sh - 100))
    screen.blit(font.render(f"{int(perc_right * 100)}%", True, (0, 0, 0)), (sw - 200, sh - 100))
    screen.blit(font.render(f"{int(curr_weight)} kg",    True, (0, 0, 0)), (sw / 2.4, sh * 0.9))