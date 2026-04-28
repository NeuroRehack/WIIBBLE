# theme.py
# Centralised DPG theme, colour palette, and font loading for WIIBBLE.
# Call apply_global_theme() once after dpg.setup_dearpygui().

import logging
import os

import dearpygui.dearpygui as dpg

from resources import FA_SOLID_FONT_PATH, resource_path

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FontAwesome 5 Solid icon codepoints used in the UI
# ---------------------------------------------------------------------------
ICON_COG = ""  # fa-cog (gear / settings)
ICON_INFINITY = "\uf534"  # fa-infinity
# Module-level handles — set by load_fonts(), used by callers
FA_ICON_FONT = NoneFA_ICON_FONT_SMALL = None  # 13px variant for inline buttons
# ---------------------------------------------------------------------------
# Crisp text font
# ---------------------------------------------------------------------------
# draw_text(size=N) upscales DPG's ~13px bitmap font to N pixels → blurry.
# Loading a real font at 100px and binding it to every draw_text item means
# ImGui downscales the 100px atlas glyph instead of upscaling a tiny one.
# Downscaling always looks crisp; upscaling never does.
TEXT_FONT = None

# Candidate font filenames — first existing one wins.
# Segoe UI (Windows 7+) is clean, neutral, and always present on Windows.
_TEXT_FONT_CANDIDATES = [
    # Bundled fonts (highest priority — drop any .ttf into assets/fonts/)
    "assets/fonts/Roboto-Regular.ttf",
]


def _find_text_font():
    """Return the resolved path to the first available text font, or None."""
    for candidate in _TEXT_FONT_CANDIDATES:
        p = resource_path(candidate)
        if os.path.exists(p):
            return p
    return None


def bind_text_font(item_tag) -> None:
    """
    Bind TEXT_FONT to a draw_text (or any) item so it renders crisply.

    Safe to call even if TEXT_FONT was not loaded (no-op in that case).
    Call this immediately after every dpg.draw_text() that should be crisp.
    """
    if TEXT_FONT is not None and dpg.does_item_exist(item_tag):
        dpg.bind_item_font(item_tag, TEXT_FONT)


# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------
C_BG_TOOLBAR = (30, 36, 48, 255)  # dark blue-grey toolbar
C_BG_WINDOW = (30, 36, 48, 255)  # same — toggle blends in
C_BTN = (55, 70, 90, 255)  # button resting
C_BTN_HOVER = (75, 95, 120, 255)  # button hover
C_BTN_ACTIVE = (107, 143, 168, 255)  # button pressed (brand teal)
C_TEXT = (220, 228, 235, 255)  # off-white text
C_TEXT_DIM = (140, 155, 170, 255)  # labels / secondary text
C_FRAME = (45, 55, 70, 255)  # slider / combo background
C_FRAME_HOVER = (60, 75, 95, 255)
C_BRAND = (107, 143, 168, 255)  # teal accent (matches canvas trail)
C_BORDER = (55, 68, 85, 255)

# Canvas drawing colours (used in ui.py)
CANVAS_BG = (250, 250, 250, 255)  # near-white canvas
CANVAS_LINE = (180, 185, 190, 255)  # soft grey crosshairs
CANVAS_LINE_W = 4  # thin crosshair lines
CANVAS_CENTRE_DOT = (80, 90, 100, 255)  # small centre marker
CANVAS_CENTRE_R = 6  # centre dot radius

BBOX_COLOR = (150, 160, 175, 180)  # muted grey bounding box
BBOX_THICKNESS = 4

# Stats bar dynamic colors
BAR_GREY_COLOR = (200, 210, 220, 255)
BAR_DARK_GREY_COLOR = (120, 120, 120, 255)
BAR_GREEN_COLOR = (80, 200, 120, 255)
BAR_ORANGE_COLOR = (255, 165, 50, 255)
BAR_RED_COLOR = (220, 60, 60, 255)


def get_stats_bar_color(percent: float):
    """
    Return the stats bar color based on percent of calibration weight.
    Discrete transitions:
        - 0-10%:   grey
        - 10-25%:  dark grey
        - 25-50%:  green
        - 50-75%:  orange
        - 75-100%: red
    """
    if percent <= 0.1:
        return BAR_GREY_COLOR
    elif percent <= 0.25:
        return BAR_DARK_GREY_COLOR
    elif percent <= 0.5:
        return BAR_GREEN_COLOR
    elif percent <= 0.75:
        return BAR_ORANGE_COLOR
    else:
        return BAR_RED_COLOR


# Stats text
STATS_TEXT_COLOR = (40, 50, 60, 255)  # dark on white canvas

# Cursor, trail and calibration screen
CURSOR_COLOR = (107, 159, 168, 255)  # circle cursor colour
TRAIL_COLOR_BASE = (107, 159, 168)  # trail RGB base (alpha fades with age)
CALIB_BG_COLOR = (110, 159, 168, 255)  # teal background for calibration screens


def load_fonts() -> None:
    """
    Load custom fonts into DPG font registry.

    Loads:
      • FontAwesome 5 Solid (icon glyphs for toolbar)
      • A system text font at 100px for crisp draw_text rendering

    MUST be called before dpg.setup_dearpygui().
    """
    global FA_ICON_FONT, FA_ICON_FONT_SMALL, TEXT_FONT

    text_font_path = _find_text_font()

    with dpg.font_registry():
        # --- FontAwesome icons ---
        if os.path.exists(FA_SOLID_FONT_PATH):
            with dpg.font(FA_SOLID_FONT_PATH, 20) as fa_font:
                dpg.add_font_range(0xF000, 0xF8FF)
            FA_ICON_FONT = fa_font
            with dpg.font(FA_SOLID_FONT_PATH, 13) as fa_font_small:
                dpg.add_font_range(0xF000, 0xF8FF)
            FA_ICON_FONT_SMALL = fa_font_small
            log.debug("FontAwesome loaded from %s", FA_SOLID_FONT_PATH)
        else:
            log.warning("FontAwesome not found at %s — using ASCII fallback", FA_SOLID_FONT_PATH)
            FA_ICON_FONT = None

        # --- Crisp text font at 100px ---
        # All draw_text calls use sizes ≤100px, so this is the ceiling.
        # ImGui downscales from 100px → any smaller size looks sharp.
        if text_font_path:
            with dpg.font(text_font_path, 100) as text_font:
                dpg.add_font_range_hint(dpg.mvFontRangeHint_Default)
            TEXT_FONT = text_font
            log.debug("Text font loaded: %s @ 100px", os.path.basename(text_font_path))
        else:
            log.warning("No system text font found — draw_text will use default (may be blurry)")
            TEXT_FONT = None


def apply_global_theme() -> None:
    """
    Apply DPG colours and styles.
    Call after dpg.setup_dearpygui(). Font loading is separate (load_fonts).
    """
    with dpg.theme() as global_theme:
        with dpg.theme_component(dpg.mvAll):
            # Window backgrounds
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, C_BG_WINDOW, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, C_BG_WINDOW, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_PopupBg, C_BG_TOOLBAR, category=dpg.mvThemeCat_Core)
            # Text
            dpg.add_theme_color(dpg.mvThemeCol_Text, C_TEXT, category=dpg.mvThemeCat_Core)
            # Buttons
            dpg.add_theme_color(dpg.mvThemeCol_Button, C_BTN, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(
                dpg.mvThemeCol_ButtonHovered, C_BTN_HOVER, category=dpg.mvThemeCat_Core
            )
            dpg.add_theme_color(
                dpg.mvThemeCol_ButtonActive, C_BTN_ACTIVE, category=dpg.mvThemeCat_Core
            )
            # Sliders / frames
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, C_FRAME, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(
                dpg.mvThemeCol_FrameBgHovered, C_FRAME_HOVER, category=dpg.mvThemeCat_Core
            )
            dpg.add_theme_color(
                dpg.mvThemeCol_FrameBgActive, C_BTN_ACTIVE, category=dpg.mvThemeCat_Core
            )
            # Slider grab
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrab, C_BRAND, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(
                dpg.mvThemeCol_SliderGrabActive, C_BTN_ACTIVE, category=dpg.mvThemeCat_Core
            )
            # Header (combo dropdown items)
            dpg.add_theme_color(dpg.mvThemeCol_Header, C_BTN, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(
                dpg.mvThemeCol_HeaderHovered, C_BTN_HOVER, category=dpg.mvThemeCat_Core
            )
            dpg.add_theme_color(
                dpg.mvThemeCol_HeaderActive, C_BTN_ACTIVE, category=dpg.mvThemeCat_Core
            )
            # Borders
            dpg.add_theme_color(dpg.mvThemeCol_Border, C_BORDER, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(
                dpg.mvThemeCol_BorderShadow, (0, 0, 0, 0), category=dpg.mvThemeCat_Core
            )
            # Scrollbar
            dpg.add_theme_color(
                dpg.mvThemeCol_ScrollbarBg, C_BG_WINDOW, category=dpg.mvThemeCat_Core
            )
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrab, C_BTN, category=dpg.mvThemeCat_Core)
            # Rounding — subtle, not pill-shaped
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 4, category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 0, category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_GrabRounding, 4, category=dpg.mvThemeCat_Core)
            # Padding
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 6, 4, category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 6, 4, category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 8, 4, category=dpg.mvThemeCat_Core)
            # No border on windows
            dpg.add_theme_style(dpg.mvStyleVar_WindowBorderSize, 0, category=dpg.mvThemeCat_Core)

    dpg.bind_theme(global_theme)
