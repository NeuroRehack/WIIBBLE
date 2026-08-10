# tests/test_imports.py
import sys


def test_import_app_does_not_load_pythonnet():
    """Mock-mode dev on Linux must not require clr/pythonnet at import time."""
    for mod in ("clr", "wiibble.board.board_connection"):
        sys.modules.pop(mod, None)

    import wiibble.app  # noqa: F401

    assert "clr" not in sys.modules
    assert "wiibble.board.board_connection" not in sys.modules
