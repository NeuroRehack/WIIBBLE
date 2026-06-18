"""Tests for background HID acquisition."""

from __future__ import annotations

from queue import Queue

from wiibble.board.acquisition import SensorAcquisition


class _PacketDevice:
    """Test double that returns queued packets from read()."""

    def __init__(self, packets: list[list[int] | None]) -> None:
        self._packets = list(packets)

    def read(self, size: int) -> list[int] | None:
        if not self._packets:
            return None
        return self._packets.pop(0)


def test_drain_latest_returns_most_recent_packet():
    """Only the newest queued report is returned to the render loop."""
    device = _PacketDevice([[1] * 32, [2] * 32, [3] * 32])
    acquisition = SensorAcquisition(device, maxsize=10)
    acquisition._queue = Queue(maxsize=10)
    for packet in ([1] * 32, [2] * 32, [3] * 32):
        acquisition._queue.put(packet)

    latest, drained = acquisition.drain_latest()

    assert drained == 3
    assert latest == [3] * 32


def test_drain_latest_empty_queue():
    """An empty queue returns None and zero drained count."""
    acquisition = SensorAcquisition(_PacketDevice([]))
    latest, drained = acquisition.drain_latest()
    assert latest is None
    assert drained == 0
