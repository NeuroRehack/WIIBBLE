#!/usr/bin/env python3
"""Extract canvas_draw and settings_panel from ui.py using AST function ranges."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI_PATH = ROOT / "src/wiibble/ui/ui.py"

CANVAS_FUNCS = {
    "_draw_canvas_counter",
    "_draw_avatar_feet_anchored",
    "_draw_avatar_trail",
    "_draw_sts_threshold_markers",
    "_sts_symmetric_offset_px",
    "draw_step_instruction",
    "draw_reference_weight_instruction",
    "draw_connection_screen",
    "draw_connection_failed_screen",
    "dashed_line_segments",
    "_draw_dashed_line",
    "_logical_rect_viewport_bounds",
    "_target_hit_at_point",
    "update_target_dwell",
    "draw_main_screen",
    "_draw_arc",
    "_format_record_limit",
    "_recording_limit_width",
    "_draw_recording_limit_text",
    "_recording_indicator_text_y",
    "_recording_indicator_layout",
    "_elapsed_timer_x",
}

SETTINGS_FUNCS = {
    "_build_section_header",
    "_cursor_label",
    "update_cursor_toggle_label",
    "_on_cursor_toggle",
    "_on_cursor_size_change",
    "_on_record_duration_change",
    "_on_start_recording",
    "_on_body_weight_change",
    "_relative_tare_label",
    "_format_tare_status",
    "update_tare_status_label",
    "_on_calibrate_board",
    "_on_board_cal_reference_change",
    "_on_calibrate_scale",
    "_build_calibration_controls",
    "_open_folder_in_file_manager",
    "_on_open_recording_folder",
    "_on_recording_prefix_change",
    "_open_recording_dir_picker",
    "_update_duration_preset_buttons",
    "_on_duration_preset_change",
    "_on_manual_duration_change",
    "_sync_open_report_browser_checkbox",
    "_on_auto_report_after_recording_change",
    "_on_open_report_in_browser_change",
    "sync_report_progress_ui",
    "_resolve_last_report_path",
    "_on_view_last_report",
    "_build_recording_controls",
    "_build_thrive_controls",
    "_on_thrive_enabled_change",
    "_on_thrive_broker_host_change",
    "_on_thrive_hub_id_change",
    "_build_cursor_controls",
    "_build_visualisation_controls",
    "build_panel_controls",
    "_on_trail_change",
    "_on_filter_change",
    "_on_show_bbox_change",
    "_on_show_global_axes_change",
    "_on_show_local_axes_change",
    "_on_target_dwell_change",
    "_on_show_target_counter_change",
    "_on_sts_enabled_change",
    "_on_sts_show_counter_change",
    "_on_sts_stand_threshold_change",
    "_on_sts_sit_threshold_change",
    "_on_sts_min_stand_change",
    "_on_sts_min_sit_change",
    "format_sts_live_status",
    "update_sts_live_status_label",
    "_on_flip_vertical_toggle",
    "_on_flip_horizontal_toggle",
    "_on_zoom_change",
    "_get_trail_active_theme",
    "_update_trail_buttons",
    "_update_flip_buttons",
}

REMOVE_FROM_UI = CANVAS_FUNCS | SETTINGS_FUNCS | {
    "ensure_textures_loaded",
    "get_wii_image_size",
    "get_person_image_size",
    "screen_cursor_radius",
    "_avatar_draw_size",
    "_crisp_text",
    "_crisp_icon_text",
    "_measure_crisp_text_width",
    "_estimate_text_width",
}

CANVAS_HEADER = '''"""Canvas and viewport drawing for WIIBBLE (Dear PyGui drawlist API)."""

from __future__ import annotations

import logging
import math
import time
from typing import Any

import dearpygui.dearpygui as dpg

from wiibble.features.data_processing import logical_to_viewport
from wiibble.features.sts_counter import sts_flank_offset_fraction
from wiibble.ui.cursor_geometry import (
    avatar_draw_size,
    logical_rect_to_viewport_bounds,
    screen_cursor_radius,
)
from wiibble.ui.draw_helpers import (
    crisp_icon_text,
    crisp_text,
    measure_crisp_text_width,
)
from wiibble.ui.textures import (
    get_connection_texture_tag,
    get_wii_texture_tag,
)
from wiibble.ui.theme import (
    BBOX_COLOR,
    BBOX_THICKNESS,
    CALIB_BG_COLOR,
    CANVAS_BG,
    CANVAS_CENTRE_DOT,
    CANVAS_CENTRE_R,
    CANVAS_LINE,
    CANVAS_LINE_DASH,
    CANVAS_LINE_GAP,
    CANVAS_LINE_W,
    CURSOR_COLOR,
    ICON_INFINITY,
    TRAIL_COLOR_BASE,
)
from wiibble.utils.constants import (
    RECORDING_INDICATOR_DOT_RADIUS,
    RECORDING_INDICATOR_LIMIT_FONT_SIZE,
    RECORDING_INDICATOR_RIGHT_MARGIN,
    RECORDING_INDICATOR_SPACING,
    RECORDING_INDICATOR_TIMER_FONT_SIZE,
    RECORDING_INDICATOR_TIMER_GAP,
    RECORDING_INDICATOR_Y,
)
from wiibble.utils.state import AppState, Settings

log = logging.getLogger(__name__)

# Calibration screen layout (fractions of canvas width/height)
CALIB_IMG_CENTRE_X = 0.25
CALIB_IMG_HEIGHT = 0.75
CALIB_IMG_VERT = 0.55
CALIB_TEXT_X = 0.57
CALIB_TEXT_TOP = 0.28
CALIB_TEXT_FONT = 0.065
CALIB_TEXT_LINE_H = 1.3
CALIB_ARC_CENTRE_X = 0.62
CALIB_ARC_CENTRE_Y = 0.41
CALIB_ARC_RADIUS = 0.18
CALIB_ARC_THICKNESS = 5
CALIB_ARC_SEGMENTS = 40
STS_TRANSITION_ZONE_COLOR = (55, 58, 65, 255)

# Aliases used by extracted draw code
_crisp_text = crisp_text
_crisp_icon_text = crisp_icon_text
_measure_crisp_text_width = measure_crisp_text_width

'''

SETTINGS_HEADER = '''"""Settings panel controls for the WIIBBLE overlay window."""

from __future__ import annotations

import logging
import os
import platform
import subprocess
from datetime import datetime
from pathlib import Path

import dearpygui.dearpygui as dpg

import wiibble.ui.theme as _theme_module
from wiibble.session_actions import (
    apply_board_cal_reference,
    apply_body_weight,
    apply_cursor_size,
    apply_filter_window,
    apply_flip_horizontal,
    apply_flip_vertical,
    apply_record_duration,
    apply_recording_dir,
    apply_recording_prefix,
    apply_setting_bool,
    apply_sts_min_dwell_seconds,
    apply_sts_sit_threshold_pct,
    apply_sts_stand_threshold_pct,
    apply_target_dwell_seconds,
    apply_thrive_broker_host,
    apply_thrive_hub_id,
    apply_trail_length,
    apply_zoom_slider,
    request_calibrate_board,
    request_calibrate_scale,
    toggle_cursor_mode,
    toggle_recording,
)
from wiibble.session_report.launcher import open_report_in_browser
from wiibble.ui.theme import (
    ICON_FLIP_HORIZONTAL,
    ICON_FLIP_VERTICAL,
    ICON_INFINITY,
)
from wiibble.utils.constants import (
    BOARD_CAL_REFERENCE_MAX,
    BOARD_CAL_REFERENCE_MIN,
    BODY_WEIGHT_MAX,
    BODY_WEIGHT_MIN,
    CURSOR_SIZE_MAX,
    CURSOR_SIZE_MIN,
    FILTER_MAX,
    FILTER_MIN,
    PANEL_BTN_H,
    PANEL_BTN_W,
    PANEL_SECTION_SPACING,
    PANEL_SLIDER_W,
    PANEL_TOGGLE_BTN_SIZE,
    PANEL_W,
    STS_MIN_DWELL_MAX,
    STS_MIN_DWELL_MIN,
    STS_MIN_DWELL_STEP,
    STS_SIT_THRESHOLD_PCT_MAX,
    STS_SIT_THRESHOLD_PCT_MIN,
    STS_STAND_THRESHOLD_PCT_MAX,
    STS_STAND_THRESHOLD_PCT_MIN,
    TARGET_DWELL_MAX,
    TARGET_DWELL_MIN,
    TARGET_DWELL_STEP,
    ZOOM_MAX,
    ZOOM_MIN,
)
from wiibble.utils.recording_names import (
    DEFAULT_RECORDING_DIR,
    normalize_recording_prefix,
    report_search_paths,
    resolve_recording_dir,
)
from wiibble.utils.state import AppState, Settings

log = logging.getLogger(__name__)

_trail_active_theme = None

'''

UI_REEXPORT = '''

# ---------------------------------------------------------------------------
# Re-exports from split UI modules (backward-compatible public API)
# ---------------------------------------------------------------------------
from wiibble.ui.canvas_draw import (  # noqa: E402
    _draw_sts_threshold_markers,
    draw_connection_failed_screen,
    draw_connection_screen,
    draw_main_screen,
    draw_reference_weight_instruction,
    draw_step_instruction,
    update_target_dwell,
)
from wiibble.ui.cursor_geometry import screen_cursor_radius  # noqa: E402
from wiibble.ui.draw_helpers import (  # noqa: E402
    crisp_icon_text as _crisp_icon_text,
    crisp_text as _crisp_text,
    estimate_text_width as _estimate_text_width,
    measure_crisp_text_width as _measure_crisp_text_width,
)
from wiibble.ui.settings_panel import (  # noqa: E402
    _format_tare_status,
    _on_start_recording,
    _on_zoom_change,
    _relative_tare_label,
    build_panel_controls,
    format_sts_live_status,
    sync_report_progress_ui,
    update_cursor_toggle_label,
    update_sts_live_status_label,
    update_tare_status_label,
)
from wiibble.ui.textures import (  # noqa: E402
    ensure_textures_loaded,
    get_person_image_size,
    get_wii_image_size,
)

'''


def extract_functions(source: str, names: set[str]) -> tuple[str, set[int]]:
    """Return concatenated source for named functions and line indices to remove."""
    mod = ast.parse(source)
    lines = source.splitlines(keepends=True)
    chunks: list[str] = []
    remove: set[int] = set()
    for node in mod.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            start, end = node.lineno - 1, node.end_lineno
            chunks.append("".join(lines[start:end]))
            chunks.append("\n")
            remove.update(range(start, end))
    return "".join(chunks), remove


def patch_canvas_body(body: str) -> str:
    """Fix references in extracted canvas code."""
    body = body.replace("_avatar_draw_size", "avatar_draw_size")
    body = body.replace("_person_texture_tag", '"person_image"')
    body = body.replace("_wii_texture_tags[", "get_wii_texture_tag(")
    # Fix get_wii_texture_tag(1 if step -> get_wii_texture_tag(1) if step - manual fix needed
    body = body.replace(
        'get_wii_texture_tag(1 if step == "on" else 0]',
        'get_wii_texture_tag(1 if step == "on" else 0)',
    )
    body = body.replace(
        "get_wii_texture_tag(2]",
        "get_wii_texture_tag(2)",
    )
    body = body.replace(
        "_connection_texture_tag",
        "get_connection_texture_tag()",
    )
    return body


def main() -> None:
    source = UI_PATH.read_text()
    canvas_body, remove_canvas = extract_functions(source, CANVAS_FUNCS)
    settings_body, remove_settings = extract_functions(source, SETTINGS_FUNCS)
    _, remove_misc = extract_functions(source, REMOVE_FROM_UI - CANVAS_FUNCS - SETTINGS_FUNCS)

    canvas_path = ROOT / "src/wiibble/ui/canvas_draw.py"
    settings_path = ROOT / "src/wiibble/ui/settings_panel.py"
    canvas_path.write_text(CANVAS_HEADER + patch_canvas_body(canvas_body))
    settings_path.write_text(SETTINGS_HEADER + settings_body)

    remove_all = remove_canvas | remove_settings | remove_misc
    lines = source.splitlines(keepends=True)
    new_ui = "".join(line for i, line in enumerate(lines) if i not in remove_all)
    if UI_REEXPORT.strip() not in new_ui:
        new_ui = new_ui.rstrip() + UI_REEXPORT
    UI_PATH.write_text(new_ui)
    print(
        f"ui.py: {len(lines)} -> {len(new_ui.splitlines())} lines; "
        f"canvas_draw {len(canvas_body.splitlines())} lines; "
        f"settings_panel {len(settings_body.splitlines())} lines"
    )


if __name__ == "__main__":
    main()
