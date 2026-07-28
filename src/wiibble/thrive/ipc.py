"""Localhost UDP IPC between WIIBBLE main app and THRIVE companion."""

from __future__ import annotations

import contextlib
import json
import logging
import socket
from typing import Any

from wiibble.thrive.config import DEFAULT_COMMAND_PORT, DEFAULT_FRAME_PORT

log = logging.getLogger(__name__)

_HOST = "127.0.0.1"


class FrameSender:
    """Non-blocking UDP sender for live frame packets."""

    def __init__(self, port: int = DEFAULT_FRAME_PORT) -> None:
        self._addr = (_HOST, port)
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setblocking(False)

    def send_frame(
        self,
        top_left: float,
        top_right: float,
        bottom_left: float,
        bottom_right: float,
        *,
        flip_horizontal: bool,
        flip_vertical: bool,
        filter_window: int,
    ) -> None:
        """Enqueue one frame; drops silently on socket errors."""
        payload = json.dumps(
            {
                "type": "frame",
                "tl": top_left,
                "tr": top_right,
                "bl": bottom_left,
                "br": bottom_right,
                "fh": flip_horizontal,
                "fv": flip_vertical,
                "fw": filter_window,
            },
            separators=(",", ":"),
        ).encode("utf-8")
        with contextlib.suppress(OSError):
            self._sock.sendto(payload, self._addr)

    def send_shutdown(self) -> None:
        """Signal the companion to exit."""
        payload = json.dumps({"type": "shutdown"}, separators=(",", ":")).encode(
            "utf-8"
        )
        with contextlib.suppress(OSError):
            self._sock.sendto(payload, self._addr)

    def close(self) -> None:
        with contextlib.suppress(OSError):
            self._sock.close()


class CommandSender:
    """Send commands from companion back to the main app."""

    def __init__(self, port: int = DEFAULT_COMMAND_PORT) -> None:
        self._addr = (_HOST, port)
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setblocking(False)

    def send_command(self, command: str) -> None:
        payload = json.dumps(
            {"type": "command", "command": command},
            separators=(",", ":"),
        ).encode("utf-8")
        try:
            self._sock.sendto(payload, self._addr)
        except OSError as exc:
            log.warning("Failed to send THRIVE command %r: %s", command, exc)

    def send_settings(self, values: dict[str, Any]) -> None:
        payload = json.dumps(
            {"type": "settings", **values},
            separators=(",", ":"),
        ).encode("utf-8")
        try:
            self._sock.sendto(payload, self._addr)
        except OSError as exc:
            log.warning("Failed to send THRIVE settings: %s", exc)

    def close(self) -> None:
        with contextlib.suppress(OSError):
            self._sock.close()


class CommandReceiver:
    """Poll inbound commands from the companion."""

    def __init__(self, port: int = DEFAULT_COMMAND_PORT) -> None:
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((_HOST, port))
        self._sock.setblocking(False)

    def drain(self) -> list[dict[str, Any]]:
        """Return all pending command/settings packets."""
        packets: list[dict[str, Any]] = []
        while True:
            try:
                data, _ = self._sock.recvfrom(4096)
            except BlockingIOError:
                break
            except OSError:
                break
            try:
                packets.append(json.loads(data.decode("utf-8")))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
        return packets

    def close(self) -> None:
        with contextlib.suppress(OSError):
            self._sock.close()


class FrameReceiver:
    """Receive frame packets in the companion process."""

    def __init__(self, port: int = DEFAULT_FRAME_PORT) -> None:
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((_HOST, port))
        self._sock.settimeout(0.005)

    @property
    def socket(self) -> socket.socket:
        return self._sock

    def recv_latest(self) -> dict[str, Any] | None:
        """Drain the UDP buffer and return the most recent frame packet."""
        latest: dict[str, Any] | None = None
        shutdown = False
        while True:
            try:
                data, _ = self._sock.recvfrom(4096)
            except TimeoutError:
                break
            except OSError as exc:
                if isinstance(exc, socket.timeout):
                    break
                break
            try:
                packet = json.loads(data.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            if packet.get("type") == "shutdown":
                shutdown = True
                continue
            if packet.get("type") == "frame":
                latest = packet
        if shutdown:
            return {"type": "shutdown"}
        return latest

    def close(self) -> None:
        with contextlib.suppress(OSError):
            self._sock.close()
