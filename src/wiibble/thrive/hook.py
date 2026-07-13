"""Non-blocking THRIVE export hook for the WIIBBLE main session loop."""

from __future__ import annotations

import logging
import subprocess
import threading
import time
from typing import Any

from wiibble.thrive.config import PUBLISH_RATE_HZ
from wiibble.thrive.ipc import CommandReceiver, FrameSender
from wiibble.thrive.launcher import launch_thrive_companion_async
from wiibble.utils.state import Settings

log = logging.getLogger(__name__)

_hook: ThriveHook | None = None
_COMPANION_STARTUP_S = 0.4


class ThriveHook:
    """Thin session hook: UDP frames out, command poll in, companion lifecycle."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._sender: FrameSender | None = None
        self._command_receiver: CommandReceiver | None = None
        self._process: subprocess.Popen | None = None
        self._active = False
        self._stop_sender = threading.Event()
        self._sender_thread: threading.Thread | None = None
        self._latest_lock = threading.Lock()
        self._latest_frame: tuple[dict[str, Any], Settings] | None = None

    def start(self) -> None:
        """Launch companion and open IPC channels."""
        if self._active:
            return
        if not self._settings.thrive_enabled:
            return

        self._sender = FrameSender()
        self._command_receiver = CommandReceiver()
        self._process = launch_thrive_companion_async(
            broker_host=self._settings.thrive_broker_host,
            hub_id=self._settings.thrive_hub_id,
            node_id=self._settings.thrive_node_id,
        )
        if self._process is None:
            log.warning("THRIVE companion unavailable — export disabled for session")
            self._cleanup_ipc()
            return

        time.sleep(_COMPANION_STARTUP_S)
        self._stop_sender.clear()
        self._sender_thread = threading.Thread(
            target=self._sender_loop,
            name="thrive-udp-sender",
            daemon=True,
        )
        self._sender_thread.start()
        self._active = True
        log.info(
            "THRIVE export started (broker=%s hub=%s)",
            self._settings.thrive_broker_host,
            self._settings.thrive_hub_id,
        )

    def stop(self) -> None:
        """Signal companion shutdown and release IPC."""
        self._stop_sender.set()
        if self._sender_thread is not None:
            self._sender_thread.join(timeout=1.0)
            self._sender_thread = None
        if self._sender is not None:
            self._sender.send_shutdown()
        if self._process is not None:
            try:
                self._process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None
        self._cleanup_ipc()
        with self._latest_lock:
            self._latest_frame = None
        self._active = False
        log.info("THRIVE export stopped")

    def _cleanup_ipc(self) -> None:
        if self._sender is not None:
            self._sender.close()
            self._sender = None
        if self._command_receiver is not None:
            self._command_receiver.close()
            self._command_receiver = None

    def publish_frame(self, frame_state: dict[str, Any], settings: Settings) -> None:
        """Store the latest frame for the background UDP sender (non-blocking)."""
        if not self._active:
            return
        with self._latest_lock:
            self._latest_frame = (frame_state, settings)

    def _sender_loop(self) -> None:
        """Send the latest frame to the companion at a steady 50 Hz."""
        interval_s = 1.0 / PUBLISH_RATE_HZ
        while not self._stop_sender.is_set():
            sender = self._sender
            with self._latest_lock:
                latest = self._latest_frame
            if sender is not None and latest is not None:
                frame_state, settings = latest
                sender.send_frame(
                    frame_state["top_left"],
                    frame_state["top_right"],
                    frame_state["bottom_left"],
                    frame_state["bottom_right"],
                    flip_horizontal=settings.flip_horizontal,
                    flip_vertical=settings.flip_vertical,
                    filter_window=settings.filter_window,
                )
            time.sleep(interval_s)

    def poll_commands(self, session_state: dict, settings: Settings) -> None:
        """Apply inbound companion commands (tare, settings sync)."""
        if self._command_receiver is None:
            return
        for packet in self._command_receiver.drain():
            packet_type = packet.get("type")
            if packet_type == "command" and packet.get("command") == "tare":
                session_state["action"] = "tare"
            elif packet_type == "settings":
                self._apply_settings(packet, settings)

    def _apply_settings(self, packet: dict[str, Any], settings: Settings) -> None:
        changed = False
        if "smoothing_window" in packet:
            window = int(packet["smoothing_window"])
            if 1 <= window <= 20 and settings.filter_window != window:
                settings.filter_window = window
                changed = True
        if "flip_horizontal" in packet:
            fh = bool(packet["flip_horizontal"])
            if settings.flip_horizontal != fh:
                settings.flip_horizontal = fh
                changed = True
        if "flip_vertical" in packet:
            fv = bool(packet["flip_vertical"])
            if settings.flip_vertical != fv:
                settings.flip_vertical = fv
                changed = True
        if changed:
            settings.save()
            log.info("THRIVE settings synced to WIIBBLE")


def get_thrive_hook(settings: Settings) -> ThriveHook:
    """Return the module-level hook, creating it when needed."""
    global _hook
    if _hook is None:
        _hook = ThriveHook(settings)
    return _hook


def reset_thrive_hook() -> None:
    """Stop and discard the module-level hook (e.g. between sessions)."""
    global _hook
    if _hook is not None:
        _hook.stop()
        _hook = None
