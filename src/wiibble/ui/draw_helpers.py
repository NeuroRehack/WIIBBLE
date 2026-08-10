"""Shared Dear PyGui draw_text helpers for crisp font rendering."""

from __future__ import annotations

import dearpygui.dearpygui as dpg

import wiibble.ui.theme as _theme_module
from wiibble.ui.theme import bind_text_font


def crisp_text(pos, text: str, color: tuple, size: int, parent) -> int:
    """Draw text with the crisp TEXT_FONT atlas bound to the item.

    Args:
        pos: (x, y) position in parent coordinates.
        text: String to draw.
        color: RGBA colour tuple.
        size: Requested font size in pixels.
        parent: Dear PyGui drawlist or parent tag.

    Returns:
        Item tag created by ``dpg.draw_text``.
    """
    tag = dpg.draw_text(pos, text, color=color, size=size, parent=parent)
    bind_text_font(tag)
    return tag


def crisp_icon_text(pos, text: str, color: tuple, size: int, parent) -> int:
    """Draw an icon glyph using the FontAwesome atlas.

    Args:
        pos: (x, y) position in parent coordinates.
        text: Icon glyph string.
        color: RGBA colour tuple.
        size: Requested font size in pixels.
        parent: Dear PyGui drawlist or parent tag.

    Returns:
        Item tag created by ``dpg.draw_text``.
    """
    tag = dpg.draw_text(pos, text, color=color, size=size, parent=parent)
    if _theme_module.FA_ICON_FONT_DRAW is not None and dpg.does_item_exist(tag):
        dpg.bind_item_font(tag, _theme_module.FA_ICON_FONT_DRAW)
    elif _theme_module.FA_ICON_FONT is not None and dpg.does_item_exist(tag):
        dpg.bind_item_font(tag, _theme_module.FA_ICON_FONT)
    return tag


def measure_crisp_text_width(text: str, size: int) -> float:
    """Measure draw_text width using the loaded crisp font atlas.

    Args:
        text: String to measure.
        size: Font size in pixels.

    Returns:
        Estimated width in pixels.
    """
    if _theme_module.TEXT_FONT is not None:
        try:
            w, _ = dpg.get_text_size(text, font=_theme_module.TEXT_FONT)
            return w * (size / 100.0)
        except Exception:
            pass
    return len(text) * size * 0.55


def estimate_text_width(text: str, font_size: int) -> int:
    """Approximate pixel width for draw_text labels.

    Args:
        text: String to measure.
        font_size: Font size in pixels.

    Returns:
        Estimated width as an integer pixel count.
    """
    return int(measure_crisp_text_width(text, font_size))
