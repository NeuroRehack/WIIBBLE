"""Entry point for the THRIVE MQTT companion (`python -m wiibble.thrive`)."""

from __future__ import annotations

import argparse
import logging
import sys

from wiibble.thrive.bridge import ThriveBridge
from wiibble.thrive.config import (
    DEFAULT_BROKER_HOST,
    DEFAULT_BROKER_PORT,
    DEFAULT_COMMAND_PORT,
    DEFAULT_FRAME_PORT,
    DEFAULT_HUB_ID,
    DEFAULT_NODE_ID,
    ThriveConfig,
)
from wiibble.utils.logging_config import configure_logging

log = logging.getLogger(__name__)


def _firmware_version() -> str:
    try:
        from importlib.metadata import version

        return version("wiibble")
    except Exception:
        return "0.0.0"


def main(argv: list[str] | None = None) -> int:
    """Run the THRIVE MQTT bridge companion."""
    parser = argparse.ArgumentParser(
        description="WIIBBLE THRIVE MQTT bridge companion.",
    )
    parser.add_argument(
        "--broker-host",
        default=DEFAULT_BROKER_HOST,
        help=f"MQTT broker hostname (default: {DEFAULT_BROKER_HOST})",
    )
    parser.add_argument(
        "--broker-port",
        type=int,
        default=DEFAULT_BROKER_PORT,
        help=f"MQTT broker port (default: {DEFAULT_BROKER_PORT})",
    )
    parser.add_argument(
        "--hub-id",
        default=DEFAULT_HUB_ID,
        help=f"THRIVE hub ID / topic prefix segment (default: {DEFAULT_HUB_ID})",
    )
    parser.add_argument(
        "--node-id",
        default=DEFAULT_NODE_ID,
        help=f"MQTT node ID (default: {DEFAULT_NODE_ID})",
    )
    parser.add_argument(
        "--frame-port",
        type=int,
        default=DEFAULT_FRAME_PORT,
        help=f"UDP port for frame IPC (default: {DEFAULT_FRAME_PORT})",
    )
    parser.add_argument(
        "--command-port",
        type=int,
        default=DEFAULT_COMMAND_PORT,
        help=f"UDP port for command IPC (default: {DEFAULT_COMMAND_PORT})",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    args = parser.parse_args(argv)

    configure_logging(level=getattr(logging, args.log_level))
    config = ThriveConfig(
        broker_host=args.broker_host,
        broker_port=args.broker_port,
        hub_id=args.hub_id,
        node_id=args.node_id,
        frame_port=args.frame_port,
        command_port=args.command_port,
    )
    bridge = ThriveBridge(config, firmware=_firmware_version())
    try:
        bridge.run()
    except Exception:
        log.exception("THRIVE bridge failed")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
