# tests/conftest.py
# Shared fixtures used across all test modules.
import pytest


@pytest.fixture
def data_struct():
    """Default data_struct matching AppState, with tare=0 on all corners."""
    return {
        "top_right": {"rawIndex": 3, "tare": 0},
        "bottom_right": {"rawIndex": 5, "tare": 0},
        "top_left": {"rawIndex": 7, "tare": 0},
        "bottom_left": {"rawIndex": 9, "tare": 0},
    }


@pytest.fixture
def zero_data():
    """A zeroed 32-byte HID report."""
    return [0] * 32


@pytest.fixture
def balanced_corners():
    """All four corners equal — represents a perfectly balanced stance."""
    return {
        "top_right": 9.0,
        "bottom_right": 9.0,
        "top_left": 9.0,
        "bottom_left": 9.0,
    }
