"""Background HID acquisition with a thread-safe latest-frame slot."""

from __future__ import annotations

import contextlib
import logging
import time
from threading import Event, Lock, Thread
from typing import Any

log = logging.getLogger(__name__)

_READ_SIZE = 32
# Wii Balance Board HID report interval (~100 Hz).
_REPORT_INTERVAL_S = 0.01
_EMPTY_READ_SLEEP_S = 0.001


class SensorAcquisition:
    """Read HID reports on a background thread and expose the latest frame."""

    def __init__(self, device: Any, *, maxsize: int = 100) -> None:
        del maxsize  # kept for API compatibility; latest-frame slot is always size 1
        self._device = device
        self._latest_lock = Lock()
        self._latest: list[int] | bytes | None = None
        self._stop = Event()
        self._thread: Thread | None = None

    def start(self) -> None:
        """Start the acquisition thread."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        with self._latest_lock:
            self._latest = None
        self._thread = Thread(
            target=self._run, name="wiibble-hid-acquisition", daemon=True
        )
        self._thread.start()
        log.debug("Sensor acquisition thread started")

    def stop(self) -> None:
        """Stop the acquisition thread and clear any buffered frame."""
        self._stop.set()
        with contextlib.suppress(Exception):
            if hasattr(self._device, "set_nonblocking"):
                self._device.set_nonblocking(1)
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        with self._latest_lock:
            self._latest = None
        log.debug("Sensor acquisition thread stopped")

    def drain_latest(self) -> tuple[list[int] | None, int]:
        """Return the newest report since the last drain and how many were consumed."""
        with self._latest_lock:
            packet = self._latest
            self._latest = None
        if packet is None:
            return None, 0
        return list(packet), 1

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                data = self._device.read(_READ_SIZE)
            except Exception as exc:
                log.warning("HID read failed in acquisition thread: %s", exc)
                time.sleep(_EMPTY_READ_SLEEP_S)
                continue
            if not data:
                time.sleep(_EMPTY_READ_SLEEP_S)
                continue
            with self._latest_lock:
                self._latest = data
