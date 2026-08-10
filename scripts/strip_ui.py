#!/usr/bin/env python3
"""Remove extracted line ranges from ui.py."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "src/wiibble/ui/ui.py"

# Ranges to DELETE (1-based inclusive) — keep orchestration in ui.py
REMOVE_RANGES = [
    (245, 348),  # textures + cursor geometry duplicates + avatar helpers
    (377, 426),  # STS markers (moved to canvas_draw)
    (1082, 2147),  # settings panel
    (2232, 2902),  # STS callbacks + all draw functions
    (2479, 2606),  # already in 2232-2902
]

# Also remove crisp text + canvas counter (148-230) — moved to canvas_draw
REMOVE_RANGES = [
    (148, 230),
    (245, 348),
    (377, 426),
    (1082, 2147),
    (2232, 2902),
]


def main() -> None:
    lines = UI.read_text().splitlines(keepends=True)
    remove = set()
    for start, end in REMOVE_RANGES:
        remove.update(range(start - 1, end))
    kept = [line for i, line in enumerate(lines) if i not in remove]
    UI.write_text("".join(kept))
    print(f"ui.py now {len(kept)} lines (was {len(lines)})")


if __name__ == "__main__":
    main()
