"""Domain exceptions for board communication."""


class DeviceError(Exception):
    """Base exception for all device communication failures."""


class DeviceConnectionError(DeviceError):
    """Raised when a connection to the device cannot be established."""


class DeviceNotFoundError(DeviceConnectionError):
    """Raised when the DLL or HID device path is missing."""


class DeviceProtocolError(DeviceError):
    """Raised when the device returns a malformed or unexpected response."""
