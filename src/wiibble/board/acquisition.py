"""Background HID acquisition with a thread-safe frame queue."""

from __future__ import annotations

import contextlib
import logging
import time
from queue import Empty, Full, Queue
from threading import Event, Thread
from typing import Any

log = logging.getLogger(__name__)

_DEFAULT_QUEUE_SIZE = 100
_READ_SIZE = 32


class SensorAcquisition:
    """Read HID reports on a background thread and expose the latest frame."""

    def __init__(self, device: Any, *, maxsize: int = _DEFAULT_QUEUE_SIZE) -> None:
        self._device = device
        self._queue: Queue[list[int] | bytes] = Queue(maxsize=maxsize)
        self._stop = Event()
        self._paused = Event()
        self._thread: Thread | None = None

    def start(self) -> None:
        """Start the acquisition thread."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._paused.clear()
        self._thread = Thread(
            target=self._run, name="wiibble-hid-acquisition", daemon=True
        )
        self._thread.start()
        log.debug("Sensor acquisition thread started")

    def stop(self) -> None:
        """Stop the acquisition thread and drain the queue."""
        self._stop.set()
        self._paused.clear()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        self._drain_queue()
        log.debug("Sensor acquisition thread stopped")

    def pause(self) -> None:
        """Pause background reads so the main thread can use blocking I/O."""
        self._paused.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        self._drain_queue()

    def resume(self) -> None:
        """Resume background reads after :meth:`pause`."""
        if self._stop.is_set():
            return
        if self._thread is None or not self._thread.is_alive():
            self.start()
            return
        self._paused.clear()

    def drain_latest(self) -> tuple[list[int] | None, int]:
        """Return the newest queued report and how many reports were consumed."""
        latest: list[int] | None = None
        reports_drained = 0
        while True:
            try:
                packet = self._queue.get_nowait()
            except Empty:
                break
            latest = list(packet)
            reports_drained += 1
        return latest, reports_drained

    def _drain_queue(self) -> None:
        while True:
            try:
                self._queue.get_nowait()
            except Empty:
                break

    def _run(self) -> None:
        while not self._stop.is_set():
            if self._paused.is_set():
                time.sleep(0.001)
                continue
            try:
                data = self._device.read(_READ_SIZE)
            except Exception as exc:
                log.warning("HID read failed in acquisition thread: %s", exc)
                continue
            if not data:
                continue
            try:
                self._queue.put_nowait(data)
            except Full:
                with contextlib.suppress(Empty):
                    self._queue.get_nowait()
                with contextlib.suppress(Full):
                    self._queue.put_nowait(data)
