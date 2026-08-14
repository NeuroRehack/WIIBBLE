"""Compile-time product features. Defaults are the full clinical build.

A Nuitka build may generate ``_product_build.py`` (gitignored) to override
these literals. Do not rewrite this module in the compiler; delete the overlay
when the build finishes so the working tree stays on the full defaults.
"""

from __future__ import annotations

FEATURE_THRIVE: bool = True
FEATURE_SESSION_REPORT: bool = True


def _apply_build_overlay() -> None:
    """Override flags from a generated overlay module when present."""
    global FEATURE_THRIVE, FEATURE_SESSION_REPORT
    try:
        from wiibble import _product_build as overlay
    except ImportError:
        return
    FEATURE_THRIVE = bool(overlay.FEATURE_THRIVE)
    FEATURE_SESSION_REPORT = bool(overlay.FEATURE_SESSION_REPORT)


_apply_build_overlay()
