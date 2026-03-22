# theme.py
# Centralised DPG theme, colour palette, and font loading for WIIBBLE.
# Call apply_global_theme() once after dpg.setup_dearpygui().

import dearpygui.dearpygui as dpg
from resources import FA_SOLID_FONT_PATH

# ---------------------------------------------------------------------------
# FontAwesome 5 Solid icon codepoints used in the UI
# ---------------------------------------------------------------------------
ICON_COG = ""   # fa-cog (gear / settings)

# Module-level handle — set by apply_global_theme(), used by callers
FA_ICON_FONT = None

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------
C_BG_TOOLBAR   = ( 30,  36,  48, 255)   # dark blue-grey toolbar
C_BG_WINDOW    = ( 30,  36,  48, 255)   # same — toggle blends in
C_BTN          = ( 55,  70,  90, 255)   # button resting
C_BTN_HOVER    = ( 75,  95, 120, 255)   # button hover
C_BTN_ACTIVE   = (107, 143, 168, 255)   # button pressed (brand teal)
C_TEXT         = (220, 228, 235, 255)   # off-white text
C_TEXT_DIM     = (140, 155, 170, 255)   # labels / secondary text
C_FRAME        = ( 45,  55,  70, 255)   # slider / combo background
C_FRAME_HOVER  = ( 60,  75,  95, 255)
C_BRAND        = (107, 143, 168, 255)   # teal accent (matches canvas trail)
C_BORDER       = ( 55,  68,  85, 255)

# Canvas drawing colours (used in ui.py)
CANVAS_BG           = (250, 250, 250, 255)   # near-white canvas
CANVAS_LINE         = (180, 185, 190, 255)   # soft grey crosshairs
CANVAS_LINE_W       = 4                      # thin crosshair lines
CANVAS_CENTRE_DOT   = ( 80,  90, 100, 255)   # small centre marker
CANVAS_CENTRE_R     = 6                      # centre dot radius

BBOX_COLOR          = (150, 160, 175, 180)   # muted grey bounding box
BBOX_THICKNESS      = 4

# Weight bar colours — teal palette instead of red/green traffic lights
BAR_BG_COLOR        = (200, 210, 220, 255)   # light grey background
BAR_LEFT_COLOR      = ( 80, 140, 180, 255)   # left side — muted blue
BAR_RIGHT_COLOR     = (107, 168, 150, 255)   # right side — muted teal-green

# Stats text
STATS_TEXT_COLOR    = ( 40,  50,  60, 255)   # dark on white canvas


def load_fonts() -> None:
    """
    Load custom fonts into DPG font registry.
    MUST be called before dpg.setup_dearpygui() — DPG only uses the
    first font registry it sees, and setup_dearpygui() finalises it.
    """
    global FA_ICON_FONT
    import os
    if os.path.exists(FA_SOLID_FONT_PATH):
        with dpg.font_registry():
            with dpg.font(FA_SOLID_FONT_PATH, 20) as fa_font:
                # Only load FA5 icon range — keeps atlas small
                dpg.add_font_range(0xF000, 0xF8FF)
        FA_ICON_FONT = fa_font
        print(f"[Theme] FontAwesome loaded from {FA_SOLID_FONT_PATH}")
    else:
        print(f"[WARN] FontAwesome not found at {FA_SOLID_FONT_PATH} — using ASCII fallback")
        FA_ICON_FONT = None


def apply_global_theme() -> None:
    """
    Apply DPG colours and styles.
    Call after dpg.setup_dearpygui(). Font loading is separate (load_fonts).
    """
    with dpg.theme() as global_theme:
        with dpg.theme_component(dpg.mvAll):
            # Window backgrounds
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg,       C_BG_WINDOW,   category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg,        C_BG_WINDOW,   category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_PopupBg,        C_BG_TOOLBAR,  category=dpg.mvThemeCat_Core)
            # Text
            dpg.add_theme_color(dpg.mvThemeCol_Text,           C_TEXT,        category=dpg.mvThemeCat_Core)
            # Buttons
            dpg.add_theme_color(dpg.mvThemeCol_Button,         C_BTN,         category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered,  C_BTN_HOVER,   category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive,   C_BTN_ACTIVE,  category=dpg.mvThemeCat_Core)
            # Sliders / frames
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg,        C_FRAME,       category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, C_FRAME_HOVER, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive,  C_BTN_ACTIVE,  category=dpg.mvThemeCat_Core)
            # Slider grab
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrab,     C_BRAND,       category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrabActive, C_BTN_ACTIVE, category=dpg.mvThemeCat_Core)
            # Header (combo dropdown items)
            dpg.add_theme_color(dpg.mvThemeCol_Header,         C_BTN,         category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered,  C_BTN_HOVER,   category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive,   C_BTN_ACTIVE,  category=dpg.mvThemeCat_Core)
            # Borders
            dpg.add_theme_color(dpg.mvThemeCol_Border,         C_BORDER,      category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_BorderShadow,   (0,0,0,0),     category=dpg.mvThemeCat_Core)
            # Scrollbar
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarBg,    C_BG_WINDOW,   category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrab,  C_BTN,         category=dpg.mvThemeCat_Core)
            # Rounding — subtle, not pill-shaped
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding,  4, category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding,  0, category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_GrabRounding,    4, category=dpg.mvThemeCat_Core)
            # Padding
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding,  6, 4, category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding,   6, 4, category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing,    8, 4, category=dpg.mvThemeCat_Core)
            # No border on windows
            dpg.add_theme_style(dpg.mvStyleVar_WindowBorderSize, 0, category=dpg.mvThemeCat_Core)

    dpg.bind_theme(global_theme)