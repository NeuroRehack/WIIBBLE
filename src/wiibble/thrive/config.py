"""THRIVE bridge configuration."""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_NODE_ID = "wiibble_01"
DEFAULT_HUB_ID = "demo"
DEFAULT_BROKER_HOST = "localhost"
DEFAULT_BROKER_PORT = 1883
DEFAULT_FRAME_PORT = 47681
DEFAULT_COMMAND_PORT = 47682
PUBLISH_RATE_HZ = 50


@dataclass(frozen=True)
class ThriveConfig:
    """Runtime configuration for the THRIVE MQTT companion."""

    broker_host: str = DEFAULT_BROKER_HOST
    broker_port: int = DEFAULT_BROKER_PORT
    hub_id: str = DEFAULT_HUB_ID
    node_id: str = DEFAULT_NODE_ID
    frame_port: int = DEFAULT_FRAME_PORT
    command_port: int = DEFAULT_COMMAND_PORT
    topic_prefix: str = "thrive"

    @property
    def topic_base(self) -> str:
        return f"{self.topic_prefix}/{self.hub_id}/nodes/{self.node_id}"
