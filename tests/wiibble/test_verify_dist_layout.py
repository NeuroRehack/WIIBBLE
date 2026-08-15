"""Dist layout verification used by the Windows build before packaging."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

_REPO_ROOT = Path(__file__).resolve().parents[2]
_VERIFY_SCRIPT = _REPO_ROOT / "scripts" / "verify_dist_layout.py"


def _load_verify_script() -> ModuleType:
    """Load ``verify_dist_layout.py`` without installing scripts/ on sys.path.

    Returns:
        The loaded layout-verifier module.
    """
    spec = importlib.util.spec_from_file_location("verify_dist_layout", _VERIFY_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


verify_script = _load_verify_script()


def _make_companion(dist_dir: Path, subdir: str, exe_name: str) -> None:
    """Create a companion folder holding an executable and one runtime file.

    Args:
        dist_dir: Main dist directory.
        subdir: Companion subdirectory name.
        exe_name: Companion executable filename.
    """
    companion_dir = dist_dir / subdir
    companion_dir.mkdir(parents=True, exist_ok=True)
    (companion_dir / exe_name).write_text("", encoding="utf-8")
    (companion_dir / "python311.dll").write_text("", encoding="utf-8")


def _make_full_dist(dist_dir: Path) -> None:
    """Create a dist tree with both companions installed.

    Args:
        dist_dir: Main dist directory to populate.
    """
    dist_dir.mkdir(parents=True, exist_ok=True)
    (dist_dir / verify_script.MAIN_EXE_NAME).write_text("", encoding="utf-8")
    _make_companion(
        dist_dir, verify_script.THRIVE_SUBDIR, verify_script.THRIVE_EXE_NAME
    )
    _make_companion(
        dist_dir,
        verify_script.SESSION_REPORT_SUBDIR,
        verify_script.SESSION_REPORT_EXE_NAME,
    )


def test_full_layout_has_no_problems(tmp_path: Path) -> None:
    dist_dir = tmp_path / "wiibble.dist"
    _make_full_dist(dist_dir)
    problems = verify_script.verify_dist_layout(
        dist_dir, expect_thrive=True, expect_session_report=True
    )
    assert problems == []


def test_missing_dist_directory_is_reported(tmp_path: Path) -> None:
    problems = verify_script.verify_dist_layout(
        tmp_path / "absent", expect_thrive=False, expect_session_report=False
    )
    assert len(problems) == 1
    assert "Dist directory missing" in problems[0]


def test_missing_main_executable_is_reported(tmp_path: Path) -> None:
    dist_dir = tmp_path / "wiibble.dist"
    _make_full_dist(dist_dir)
    (dist_dir / verify_script.MAIN_EXE_NAME).unlink()
    problems = verify_script.verify_dist_layout(
        dist_dir, expect_thrive=True, expect_session_report=True
    )
    assert any("Main executable missing" in problem for problem in problems)


def test_missing_thrive_companion_is_reported(tmp_path: Path) -> None:
    """Regression guard for the failure that broke Build (develop) #13."""
    dist_dir = tmp_path / "wiibble.dist"
    _make_full_dist(dist_dir)
    (dist_dir / verify_script.THRIVE_SUBDIR / verify_script.THRIVE_EXE_NAME).unlink()
    problems = verify_script.verify_dist_layout(
        dist_dir, expect_thrive=True, expect_session_report=True
    )
    assert any(verify_script.THRIVE_EXE_NAME in problem for problem in problems)


def test_companion_without_runtime_files_is_reported(tmp_path: Path) -> None:
    dist_dir = tmp_path / "wiibble.dist"
    _make_full_dist(dist_dir)
    (dist_dir / verify_script.THRIVE_SUBDIR / "python311.dll").unlink()
    problems = verify_script.verify_dist_layout(
        dist_dir, expect_thrive=True, expect_session_report=True
    )
    assert any("copy was incomplete" in problem for problem in problems)


def test_lite_layout_rejects_leftover_companions(tmp_path: Path) -> None:
    dist_dir = tmp_path / "wiibble.dist"
    _make_full_dist(dist_dir)
    problems = verify_script.verify_dist_layout(
        dist_dir, expect_thrive=False, expect_session_report=False
    )
    assert len(problems) == 2
    assert all("feature is off" in problem for problem in problems)


def test_lite_layout_without_companions_is_clean(tmp_path: Path) -> None:
    dist_dir = tmp_path / "wiibble.dist"
    dist_dir.mkdir(parents=True)
    (dist_dir / verify_script.MAIN_EXE_NAME).write_text("", encoding="utf-8")
    problems = verify_script.verify_dist_layout(
        dist_dir, expect_thrive=False, expect_session_report=False
    )
    assert problems == []
