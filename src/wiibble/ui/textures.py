"""Dear PyGui texture registry for calibration and cursor images."""

from __future__ import annotations

import dearpygui.dearpygui as dpg

from wiibble.utils.resources import CONNECTION_PATH, IMAGE_PATHS, PERSON_IMAGE_PATH

_textures_loaded = False
_wii_texture_tags: list[str] = []
_person_texture_tag = "person_image"
_connection_texture_tag = "connection_image"


def ensure_textures_loaded() -> None:
    """Load all images into DPG texture registry on first call."""
    global _textures_loaded, _wii_texture_tags
    if _textures_loaded:
        return

    with dpg.texture_registry():
        for i, path in enumerate(IMAGE_PATHS):
            w, h, _, data = dpg.load_image(path)
            tag = f"wii_image_{i}"
            dpg.add_static_texture(w, h, data, tag=tag)
            _wii_texture_tags.append(tag)

        w, h, _, data = dpg.load_image(PERSON_IMAGE_PATH)
        dpg.add_static_texture(w, h, data, tag=_person_texture_tag)

        w, h, _, data = dpg.load_image(CONNECTION_PATH)
        dpg.add_static_texture(w, h, data, tag=_connection_texture_tag)

    _textures_loaded = True


def get_wii_image_size(index: int) -> tuple[int, int]:
    """Return (width, height) of a wii calibration image.

    Args:
        index: Index into the calibration image list.

    Returns:
        Texture width and height in pixels.
    """
    cfg = dpg.get_item_configuration(_wii_texture_tags[index])
    return cfg["width"], cfg["height"]


def get_wii_texture_tag(index: int) -> str:
    """Return the DPG tag for a calibration image texture.

    Args:
        index: Index into the calibration image list.

    Returns:
        Dear PyGui texture tag string.
    """
    return _wii_texture_tags[index]


def get_connection_texture_tag() -> str:
    """Return the DPG tag for the connection-failed screen image.

    Returns:
        Dear PyGui texture tag string.
    """
    return _connection_texture_tag


def get_person_image_size() -> tuple[int, int]:
    """Return the width and height of the person cursor texture.

    Returns:
        Texture width and height in pixels.
    """
    cfg = dpg.get_item_configuration(_person_texture_tag)
    return cfg["width"], cfg["height"]
