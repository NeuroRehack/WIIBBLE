"""Compile-time product profile flags and overlay writer."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from wiibble.session import (
    _publish_thrive_frame,
    _start_thrive_hook,
    apply_compile_time_feature_overrides,
)
from wiibble.utils.state import Settings

_REPO_ROOT = Path(__file__).resolve().parents[2]
_OVERLAY_SCRIPT = _REPO_ROOT / "scripts" / "write_product_overlay.py"
_PRODUCT_SOURCE = _REPO_ROOT / "src" / "wiibble" / "product.py"


def _load_overlay_script() -> ModuleType:
    """Load ``write_product_overlay.py`` without installing scripts/ on sys.path.

    Returns:
        The loaded overlay-writer module.
    """
    spec = importlib.util.spec_from_file_location(
        "write_product_overlay", _OVERLAY_SCRIPT
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


overlay_script = _load_overlay_script()


def test_committed_product_defaults_are_full() -> None:
    """Committed product.py must default both features on (full clinical build)."""
    text = _PRODUCT_SOURCE.read_text(encoding="utf-8")
    assert "FEATURE_THRIVE: bool = True" in text
    assert "FEATURE_SESSION_REPORT: bool = True" in text


def test_resolve_full_profile_enables_both() -> None:
    thrive, session_report = overlay_script.resolve_product_features(profile="full")
    assert thrive is True
    assert session_report is True


def test_resolve_lite_profile_disables_both() -> None:
    thrive, session_report = overlay_script.resolve_product_features(profile="lite")
    assert thrive is False
    assert session_report is False


def test_resolve_env_overrides_full_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WIIBBLE_PROFILE", "full")
    monkeypatch.setenv("WIIBBLE_FEATURE_THRIVE", "0")
    monkeypatch.setenv("WIIBBLE_FEATURE_SESSION_REPORT", "false")
    thrive, session_report = overlay_script.resolve_product_features()
    assert thrive is False
    assert session_report is False


def test_resolve_unknown_profile_raises() -> None:
    with pytest.raises(ValueError, match="full"):
        overlay_script.resolve_product_features(profile="custom")


def test_app_flavor_suffix() -> None:
    assert overlay_script.app_flavor_suffix(True, True) == ""
    assert overlay_script.app_flavor_suffix(False, False) == "lite"
    assert overlay_script.app_flavor_suffix(False, True) == "no-thrive"
    assert overlay_script.app_flavor_suffix(True, False) == "no-reports"


def test_write_overlay_only_when_a_feature_is_off(tmp_path: Path) -> None:
    overlay_path = tmp_path / "_product_build.py"
    written = overlay_script.write_product_overlay(
        False, True, overlay_path=overlay_path
    )
    assert written == overlay_path
    text = overlay_path.read_text(encoding="utf-8")
    assert "FEATURE_THRIVE: bool = False" in text
    assert "FEATURE_SESSION_REPORT: bool = True" in text

    overlay_path.write_text("stale\n", encoding="utf-8")
    assert (
        overlay_script.write_product_overlay(True, True, overlay_path=overlay_path)
        is None
    )
    assert not overlay_path.is_file()


def test_overlay_main_emits_compiler_flags(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    overlay_path = tmp_path / "_product_build.py"
    monkeypatch.setenv("WIIBBLE_PROFILE", "lite")
    assert overlay_script.main(["--overlay-path", str(overlay_path)]) == 0
    captured = capsys.readouterr()
    assert "THRIVE=0" in captured.out
    assert "SESSION_REPORT=0" in captured.out
    assert "APP_FLAVOR=lite" in captured.out
    assert overlay_path.is_file()


def test_overlay_main_emits_flavor_sentinel_for_full_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """An empty APP_FLAVOR would be parsed by compiler.bat as the literal '%B'."""
    overlay_path = tmp_path / "_product_build.py"
    monkeypatch.setenv("WIIBBLE_PROFILE", "full")
    monkeypatch.delenv("WIIBBLE_FEATURE_THRIVE", raising=False)
    monkeypatch.delenv("WIIBBLE_FEATURE_SESSION_REPORT", raising=False)
    assert overlay_script.main(["--overlay-path", str(overlay_path)]) == 0
    captured = capsys.readouterr()
    assert f"APP_FLAVOR={overlay_script.NO_FLAVOR_SENTINEL}\n" in captured.out
    for line in captured.out.splitlines():
        assert not line.endswith("=")


def test_apply_compile_time_overrides_does_not_save(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(thrive_enabled=True, auto_report_after_recording=True)
    monkeypatch.setattr("wiibble.product.FEATURE_THRIVE", False)
    monkeypatch.setattr("wiibble.product.FEATURE_SESSION_REPORT", False)
    with patch.object(settings, "save") as save:
        apply_compile_time_feature_overrides(settings)
    save.assert_not_called()
    assert settings.thrive_enabled is False
    assert settings.auto_report_after_recording is False


def test_publish_thrive_frame_skipped_when_feature_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(thrive_enabled=True)
    monkeypatch.setattr("wiibble.product.FEATURE_THRIVE", False)
    with patch("wiibble.session.get_thrive_hook") as get_hook:
        _publish_thrive_frame({"top_left": 0.0}, settings)
    get_hook.assert_not_called()


def test_start_thrive_hook_skipped_when_feature_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(thrive_enabled=True)
    monkeypatch.setattr("wiibble.product.FEATURE_THRIVE", False)
    with patch("wiibble.session.get_thrive_hook") as get_hook:
        assert _start_thrive_hook(settings) is None
    get_hook.assert_not_called()


def test_publish_thrive_frame_calls_hook_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(thrive_enabled=True)
    monkeypatch.setattr("wiibble.product.FEATURE_THRIVE", True)
    hook = MagicMock()
    with patch("wiibble.session.get_thrive_hook", return_value=hook) as get_hook:
        frame = {"top_left": 1.0}
        _publish_thrive_frame(frame, settings)
    get_hook.assert_called_once_with(settings)
    hook.publish_frame.assert_called_once_with(frame, settings)
