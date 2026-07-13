"""MQTT bridge loop for the THRIVE companion process."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from wiibble.thrive.announce import build_announce
from wiibble.thrive.config import PUBLISH_RATE_HZ, ThriveConfig
from wiibble.thrive.ipc import CommandSender, FrameReceiver
from wiibble.thrive.transform import (
    board_orientation_from_flips,
    cop_offset_from_channels,
    flips_from_board_orientation,
    frame_to_channels,
)

log = logging.getLogger(__name__)

_VALID_SETTINGS = frozenset({"smoothing_window", "board_orientation"})


class PublishThrottle:
    """Limit outbound MQTT data publishes to a target rate."""

    def __init__(self, rate_hz: float = PUBLISH_RATE_HZ) -> None:
        self._interval_s = 1.0 / rate_hz
        self._last_publish = float("-inf")

    def should_publish(self, now: float | None = None) -> bool:
        """Return True when enough time has elapsed since the last publish."""
        ts = now if now is not None else time.monotonic()
        if ts - self._last_publish >= self._interval_s - 1e-9:
            self._last_publish = ts
            return True
        return False

    def reset(self) -> None:
        self._last_publish = float("-inf")


class ThriveBridge:
    """MQTT sensor node publishing live WIIBBLE data at 50 Hz."""

    def __init__(self, config: ThriveConfig, firmware: str) -> None:
        import paho.mqtt.client as mqtt

        self._config = config
        self._announce = build_announce(firmware, node_id=config.node_id)
        self._topic_base = config.topic_base
        self._status_offline = {
            "node_id": config.node_id,
            "online": False,
            "state": "offline",
        }
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message

        self._command_sender = CommandSender(config.command_port)
        self._frame_receiver = FrameReceiver(config.frame_port)

        self._cop_offset_x_kg = 0.0
        self._cop_offset_y_kg = 0.0
        self._smoothing_window = 5
        self._board_orientation = "standard"
        self._last_raw_channels: dict[str, Any] | None = None
        self._last_frame_at = 0.0
        self._sequence = 0
        self._running = True
        self._publish_interval_s = 1.0 / PUBLISH_RATE_HZ
        self._frame_stale_s = 0.5

    def _on_connect(
        self,
        client: Any,
        userdata: Any,
        flags: Any,
        reason_code: Any,
        properties: Any,
    ) -> None:
        if reason_code.is_failure:
            log.error("MQTT connect failed: %s", reason_code)
            return
        log.info("Connected to broker as %s", self._config.node_id)
        client.publish(
            f"{self._topic_base}/announce",
            json.dumps(self._announce),
            qos=1,
            retain=True,
        )
        client.publish(
            f"{self._topic_base}/status",
            json.dumps(
                {
                    "node_id": self._config.node_id,
                    "online": True,
                    "ts": time.time(),
                    "state": "active",
                }
            ),
            qos=1,
            retain=True,
        )
        client.publish(
            f"{self._topic_base}/settings",
            json.dumps(self._settings_payload()),
            qos=1,
            retain=True,
        )
        client.subscribe(f"{self._topic_base}/command", qos=1)
        client.subscribe(f"{self._topic_base}/settings/set", qos=1)

    def _on_message(self, client: Any, userdata: Any, msg: Any) -> None:
        try:
            payload = json.loads(msg.payload.decode())
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            log.warning("Bad MQTT payload on %s: %s", msg.topic, exc)
            return
        if msg.topic.endswith("/command"):
            self._handle_command(payload)
        elif msg.topic.endswith("/settings/set"):
            self._handle_settings_set(payload)

    def _settings_payload(self) -> dict[str, Any]:
        return {
            "node_id": self._config.node_id,
            "ts": time.time(),
            "values": {
                "smoothing_window": self._smoothing_window,
                "board_orientation": self._board_orientation,
            },
        }

    def _publish_settings(self) -> None:
        self._client.publish(
            f"{self._topic_base}/settings",
            json.dumps(self._settings_payload()),
            qos=1,
            retain=True,
        )

    def _ack(
        self,
        request_id: str | None,
        command: str,
        status: str,
        message: str | None = None,
    ) -> None:
        if request_id is None:
            return
        response: dict[str, Any] = {
            "node_id": self._config.node_id,
            "request_id": request_id,
            "command": command,
            "status": status,
            "ts": time.time(),
        }
        if message:
            response["message"] = message
        self._client.publish(
            f"{self._topic_base}/command_response",
            json.dumps(response),
            qos=1,
            retain=False,
        )

    def _handle_command(self, payload: dict[str, Any]) -> None:
        command = payload.get("command")
        request_id = payload.get("request_id")
        log.info("Command received: %s", command)

        if command == "tare":
            if self._last_raw_channels is not None:
                ox, oy = cop_offset_from_channels(self._last_raw_channels)
                self._cop_offset_x_kg += ox
                self._cop_offset_y_kg += oy
            self._command_sender.send_command("tare")
            log.info("Tare applied (CoP offset updated, WIIBBLE tare requested)")
            self._ack(request_id, "tare", "ok")
            return

        self._ack(
            request_id,
            command or "unknown",
            "error",
            message=f"Unknown command: {command!r}",
        )

    def _handle_settings_set(self, payload: dict[str, Any]) -> None:
        request_id = payload.get("request_id")
        errors: list[str] = []
        settings_update: dict[str, Any] = {}

        for key, value in payload.items():
            if key == "request_id":
                continue
            if key not in _VALID_SETTINGS:
                errors.append(f"Unknown setting: {key!r}")
                continue
            try:
                if key == "smoothing_window":
                    window = int(value)
                    if not 1 <= window <= 20:
                        raise ValueError("out of range 1-20")
                    self._smoothing_window = window
                    settings_update["smoothing_window"] = window
                elif key == "board_orientation":
                    if value not in ("standard", "rotated-180"):
                        raise ValueError("must be 'standard' or 'rotated-180'")
                    self._board_orientation = value
                    settings_update["board_orientation"] = value
                    fh, fv = flips_from_board_orientation(value)
                    settings_update["flip_horizontal"] = fh
                    settings_update["flip_vertical"] = fv
            except (ValueError, TypeError) as exc:
                errors.append(f"{key}: {exc}")

        if errors:
            self._ack(request_id, "settings_set", "error", message="; ".join(errors))
            return

        if settings_update:
            self._command_sender.send_settings(settings_update)
        self._publish_settings()
        log.info(
            "Settings updated: smoothing=%d orientation=%s",
            self._smoothing_window,
            self._board_orientation,
        )
        self._ack(request_id, "settings_set", "ok")

    def _publish_data(self, channels: dict[str, Any]) -> None:
        self._client.publish(
            f"{self._topic_base}/data",
            json.dumps(
                {
                    "node_id": self._config.node_id,
                    "ts": time.time(),
                    "seq": self._sequence,
                    "channels": channels,
                }
            ),
            qos=0,
        )
        self._sequence += 1

    def _process_frame(self, packet: dict[str, Any]) -> None:
        flip_h = bool(packet.get("fh", False))
        flip_v = bool(packet.get("fv", False))
        filter_window = int(packet.get("fw", 1))
        self._smoothing_window = filter_window
        self._board_orientation = board_orientation_from_flips(flip_h, flip_v)

        channels = frame_to_channels(
            float(packet["tl"]),
            float(packet["tr"]),
            float(packet["bl"]),
            float(packet["br"]),
            flip_horizontal=flip_h,
            flip_vertical=flip_v,
            cop_offset_x_kg=self._cop_offset_x_kg,
            cop_offset_y_kg=self._cop_offset_y_kg,
            board_orientation=self._board_orientation,
        )
        self._last_raw_channels = channels
        self._last_frame_at = time.monotonic()

    def _maybe_publish_latest(self, now: float) -> None:
        """Publish the latest channels at 50 Hz while frames are fresh."""
        if self._last_raw_channels is None:
            return
        if now - self._last_frame_at > self._frame_stale_s:
            return
        if now >= self._next_publish_at:
            self._publish_data(self._last_raw_channels)
            self._next_publish_at = now + self._publish_interval_s

    def run(self) -> None:
        """Connect to broker and process frames until shutdown."""
        try:
            self._client.will_set(
                f"{self._topic_base}/status",
                json.dumps(self._status_offline),
                qos=1,
                retain=True,
            )
            self._client.connect(self._config.broker_host, self._config.broker_port)
        except OSError as exc:
            log.error("Failed to connect to MQTT broker: %s", exc)
            return

        self._client.loop_start()
        log.info(
            "THRIVE bridge listening on UDP :%d (commands → :%d)",
            self._config.frame_port,
            self._config.command_port,
        )

        self._next_publish_at = time.monotonic()
        try:
            while self._running:
                packet = self._frame_receiver.recv_latest()
                if packet is not None:
                    if packet.get("type") == "shutdown":
                        log.info("Shutdown received from main app")
                        break
                    if packet.get("type") == "frame":
                        self._process_frame(packet)

                now = time.monotonic()
                self._maybe_publish_latest(now)
                sleep_s = self._next_publish_at - time.monotonic()
                if sleep_s > 0:
                    time.sleep(sleep_s)
        except KeyboardInterrupt:
            log.info("Interrupted")
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        """Publish offline status and release resources."""
        self._running = False
        self._client.publish(
            f"{self._topic_base}/status",
            json.dumps(self._status_offline),
            qos=1,
            retain=True,
        )
        time.sleep(0.15)
        self._client.loop_stop()
        self._client.disconnect()
        self._frame_receiver.close()
        self._command_sender.close()
