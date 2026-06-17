# tests/test_display.py
import sys

from wiibble.utils.display import _DEFAULT_SCREEN_SIZE, get_screen_size


class TestGetScreenSize:
    def test_returns_positive_integers(self):
        w, h = get_screen_size()
        assert isinstance(w, int)
        assert isinstance(h, int)
        assert w > 0
        assert h > 0

    def test_non_windows_fallback_when_tk_import_fails(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")

        import wiibble.utils.display as display_mod

        real_import = __import__

        def mock_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "tkinter":
                raise ImportError("tkinter unavailable in test")
            return real_import(name, globals, locals, fromlist, level)

        monkeypatch.setattr("builtins.__import__", mock_import)
        w, h = display_mod.get_screen_size()
        assert (w, h) == _DEFAULT_SCREEN_SIZE


class TestDefaultScreenSize:
    def test_default_constants(self):
        assert _DEFAULT_SCREEN_SIZE == (1280, 720)
