#!/usr/bin/env python3
"""One-off script to extract canvas_draw and settings_panel from ui.py."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "src/wiibble/ui/ui.py"

# (start_line, end_line) inclusive, 1-based
CANVAS_RANGES = [
    (148, 230),  # crisp text helpers + canvas counter
    (296, 348),  # avatar draw helpers
    (377, 426),  # STS threshold markers
    (2281, 2902),  # draw_* through end of draw_main_screen
    (2479, 2606),  # dashed lines, target hit, dwell (between draw blocks)
]

SETTINGS_RANGES = [
    (1082, 2147),  # section headers through build_panel_controls
    (1120, 1280),  # cursor/recording callbacks overlapping - handled by range above
    (2232, 2278),  # STS live status + flip/zoom callbacks after build_panel
]

# Re-read - SETTINGS should be 1082-2147 and 2232-2278
SETTINGS_RANGES = [
    (1082, 2147),
    (2232, 2278),
]


def extract_lines(path: Path, ranges: list[tuple[int, int]]) -> str:
    """Return concatenated line ranges from path."""
    lines = path.read_text().splitlines(keepends=True)
    chunks: list[str] = []
    for start, end in ranges:
        chunks.append("".join(lines[start - 1 : end]))
    return "".join(chunks)


def main() -> None:
    canvas_body = extract_lines(UI, CANVAS_RANGES)
    settings_body = extract_lines(UI, SETTINGS_RANGES)

    canvas_header = '''"""Canvas and viewport drawing for WIIBBLE (Dear PyGui drawlist API)."""

from __future__ import annotations

import logging
import math
import time
from typing import Any

import dearpygui.dearpygui as dpg

import wiibble.ui.theme as _theme_module
from wiibble.features.data_processing import logical_to_viewport
from wiibble.features.sts_counter import (
    format_sts_state_label,
    sts_flank_offset_fraction,
    weight_pct_of_body,
)
from wiibble.ui.cursor_geometry import (
    logical_rect_to_viewport_bounds,
    screen_cursor_radius,
    trail_size_fraction,
    trail_stamp_alpha,
)
from wiibble.ui.textures import get_person_image_size
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
    TRAIL_COLOR_BASE,
    bind_text_font,
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

'''

    settings_header = '''"""Settings panel controls for the WIIBBLE overlay window."""

from __future__ import annotations

import logging
import os
import platform
import subprocess
from datetime import datetime
from pathlib import Path

import dearpygui.dearpygui as dpg

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
    PANEL_BTN_H,
    PANEL_BTN_W,
    PANEL_SECTION_SPACING,
    PANEL_SLIDER_W,
    PANEL_TOGGLE_BTN_SIZE,
    PANEL_W,
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

'''

    (ROOT / "src/wiibble/ui/canvas_draw.py").write_text(canvas_header + canvas_body)
    (ROOT / "src/wiibble/ui/settings_panel.py").write_text(settings_header + settings_body)
    print("Wrote canvas_draw.py and settings_panel.py")


if __name__ == "__main__":
    main()
