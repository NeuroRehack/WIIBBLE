"""Verify the Nuitka output layout before packaging.

Companion executables are copied into the main dist by ``compiler.bat``. A copy that
silently produces nothing leaves a dist that installs fine but cannot start its
companions, so the build fails here rather than shipping a broken installer.
"""

from __future__ import annotations

import argparse
import importlib.util
import logging
import sys
from pathlib import Path
from types import ModuleType

from wiibble.session_report.launcher import (
    SESSION_REPORT_EXE_NAME,
    SESSION_REPORT_SUBDIR,
)
from wiibble.thrive.launcher import THRIVE_EXE_NAME, THRIVE_SUBDIR

log = logging.getLogger(__name__)

# Matches --output-filename in compiler.bat.
MAIN_EXE_NAME = "WIIBBLE.exe"
DEFAULT_DIST_DIR = Path("dist_nuitka") / "wiibble.dist"


def _repo_root() -> Path:
    """Return the repository root, one level above this script."""
    return Path(__file__).resolve().parent.parent


def _load_product_flags_module() -> ModuleType:
    """Load the sibling overlay writer without putting scripts/ on ``sys.path``.

    Returns:
        The loaded ``write_product_overlay`` module.

    Raises:
        ImportError: If the sibling script cannot be loaded.
    """
    script_path = Path(__file__).resolve().parent / "write_product_overlay.py"
    spec = importlib.util.spec_from_file_location("write_product_overlay", script_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_dist_layout(
    dist_dir: Path,
    *,
    expect_thrive: bool,
    expect_session_report: bool,
) -> list[str]:
    """Check that the built dist matches the compiled feature set.

    Args:
        dist_dir: Nuitka standalone output directory holding ``WIIBBLE.exe``.
        expect_thrive: Whether the THRIVE companion should be installed.
        expect_session_report: Whether the session-report companion should be
            installed.

    Returns:
        Human-readable problem descriptions. Empty when the layout is correct.
    """
    problems: list[str] = []

    if not dist_dir.is_dir():
        return [f"Dist directory missing: {dist_dir}"]

    main_exe = dist_dir / MAIN_EXE_NAME
    if not main_exe.is_file():
        problems.append(f"Main executable missing: {main_exe}")

    companions = (
        (expect_thrive, THRIVE_SUBDIR, THRIVE_EXE_NAME),
        (expect_session_report, SESSION_REPORT_SUBDIR, SESSION_REPORT_EXE_NAME),
    )
    for expected, subdir, exe_name in companions:
        companion_dir = dist_dir / subdir
        companion_exe = companion_dir / exe_name
        if expected:
            if not companion_exe.is_file():
                problems.append(f"Companion executable missing: {companion_exe}")
            elif len(list(companion_dir.iterdir())) < 2:
                # A standalone dist is an exe plus its runtime, never the exe alone.
                problems.append(
                    f"Companion at {companion_dir} holds only the executable, "
                    "the copy was incomplete"
                )
        elif companion_dir.exists():
            problems.append(
                f"Companion directory {companion_dir} present but the feature is off"
            )

    return problems


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse CLI arguments for the layout verifier.

    Args:
        argv: Argument list excluding the program name. None uses ``sys.argv``.

    Returns:
        Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Verify the WIIBBLE Nuitka dist layout before packaging."
    )
    parser.add_argument(
        "--dist-dir",
        type=Path,
        default=None,
        help=f"Dist directory to check. Defaults to {DEFAULT_DIST_DIR}.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Verify the dist layout for the profile the build was compiled with.

    Args:
        argv: Argument list excluding the program name.

    Returns:
        Process exit code (0 when the layout is correct, 1 otherwise).
    """
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stderr,
        format="[verify-dist] %(message)s",
    )
    args = _parse_args(argv)
    dist_dir = (
        args.dist_dir if args.dist_dir is not None else _repo_root() / DEFAULT_DIST_DIR
    )

    product_flags = _load_product_flags_module()
    try:
        thrive, session_report = product_flags.resolve_product_features()
    except ValueError as exc:
        log.error("%s", exc)
        return 1

    log.info(
        "Checking %s (thrive=%s, session_report=%s)", dist_dir, thrive, session_report
    )
    problems = verify_dist_layout(
        dist_dir, expect_thrive=thrive, expect_session_report=session_report
    )
    for problem in problems:
        log.error("%s", problem)
    if problems:
        return 1

    log.info("Dist layout OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
