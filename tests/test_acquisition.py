"""Tests for background HID acquisition."""

from __future__ import annotations

import time
from threading import Event

from wiibble.board.acquisition import SensorAcquisition


class _PacketDevice:
    """Test double that returns queued packets from read()."""

    def __init__(
        self,
        packets: list[list[int] | None] | None = None,
        *,
        nonblocking: bool = True,
    ) -> None:
        self._packets = list(packets or [])
        self._nonblocking = nonblocking
        self.nonblocking_calls: list[int] = []

    def set_nonblocking(self, nonblocking: int) -> None:
        self._nonblocking = bool(nonblocking)
        self.nonblocking_calls.append(nonblocking)

    def read(self, size: int) -> list[int] | None:
        if self._packets:
            return self._packets.pop(0)
        return [] if self._nonblocking else None


def test_drain_latest_returns_most_recent_packet():
    """Only the newest unread report is returned to the render loop."""
    device = _PacketDevice([[1] * 32, [2] * 32, [3] * 32])
    acquisition = SensorAcquisition(device)
    acquisition.start()
    time.sleep(0.05)
    latest, drained = acquisition.drain_latest()
    acquisition.stop()

    assert drained == 1
    assert latest == [3] * 32


def test_drain_latest_empty_queue():
    """An empty slot returns None and zero drained count."""
    acquisition = SensorAcquisition(_PacketDevice([]))
    latest, drained = acquisition.drain_latest()
    assert latest is None
    assert drained == 0


def test_stop_sets_nonblocking_before_join():
    """Stopping unblocks a pending HID read before joining the worker thread."""
    release = Event()
    device = _BlockingUntilReleasedDevice(release)
    acquisition = SensorAcquisition(device)
    acquisition.start()
    time.sleep(0.02)
    acquisition.stop()
    assert device.nonblocking_calls == [1]


class _BlockingUntilReleasedDevice:
    def __init__(self, release: Event) -> None:
        self._release = release
        self.nonblocking_calls: list[int] = []
        self._nonblocking = False

    def set_nonblocking(self, nonblocking: int) -> None:
        self._nonblocking = bool(nonblocking)
        self.nonblocking_calls.append(nonblocking)
        if self._nonblocking:
            self._release.set()

    def read(self, size: int) -> list[int]:
        if not self._nonblocking:
            self._release.wait(timeout=1.0)
        return [1] * size
