"""Tests for board device exception hierarchy."""

from wiibble.board.exceptions import (
    DeviceConnectionError,
    DeviceError,
    DeviceNotFoundError,
    DeviceProtocolError,
)


def test_device_errors_are_subclasses():
    assert issubclass(DeviceNotFoundError, DeviceError)
    assert issubclass(DeviceConnectionError, DeviceError)
    assert issubclass(DeviceProtocolError, DeviceError)
