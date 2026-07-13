"""Announce payload schema parity with THRIVE thrive-sim-wiibble."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from wiibble.thrive.announce import build_announce

THRIVE_SIM_PATH = (
    Path.home() / "Sandbox" / "THRIVE" / "src" / "thrive" / "sims" / "wiibble.py"
)


def _required_announce_keys() -> set[str]:
    return {
        "node_id",
        "node_class",
        "node_type",
        "label",
        "firmware",
        "schema_version",
        "channels",
        "signals_offered",
        "commands",
        "settings",
    }


def _channel_names(channels: list) -> set[str]:
    return {ch["name"] for ch in channels}


@pytest.mark.parametrize(
    ("field", "expected"),
    [
        ("node_class", "sensor"),
        ("node_type", "balance_board"),
        ("schema_version", "1"),
    ],
)
def test_announce_core_fields_match_simulator(field: str, expected: str):
    announce = build_announce("2.1.0")
    assert announce[field] == expected


def test_announce_has_required_keys():
    announce = build_announce("2.1.0")
    assert _required_announce_keys() <= set(announce.keys())


def test_announce_channel_names_match_simulator():
    announce = build_announce("2.1.0")
    expected = {"cop_x_mm", "cop_y_mm", "total_weight_kg", "quadrant_kg"}
    assert _channel_names(announce["channels"]) == expected


def test_announce_signals_offered_types():
    announce = build_announce("2.1.0")
    types = [s["signal_type"] for s in announce["signals_offered"]]
    assert types == ["vector2", "scalar", "quadrant"]


def test_announce_commands_include_tare():
    announce = build_announce("2.1.0")
    names = [c["name"] for c in announce["commands"]]
    assert "tare" in names


def test_announce_settings_match_simulator_names():
    announce = build_announce("2.1.0")
    names = {s["name"] for s in announce["settings"]}
    assert names == {"smoothing_window", "board_orientation"}


def test_announce_node_identity_distinct_from_simulator():
    announce = build_announce("2.1.0", node_id="wiibble_01", label="WIIBBLE")
    assert announce["node_id"] == "wiibble_01"
    assert announce["label"] == "WIIBBLE"
    assert announce["node_id"] != "wiibble_sim_01"


def _load_thrive_sim_announce() -> dict:
    """Load ANNOUNCE from THRIVE wiibble.py without importing thrive package."""
    text = THRIVE_SIM_PATH.read_text(encoding="utf-8")
    end = text.index("\n\n\ndef quadrants_from_cop")
    start = text.index("ANNOUNCE")
    chunk = text[start:end].replace("ANNOUNCE: dict[str, Any] = ", "ANNOUNCE = ")
    namespace = {
        "NODE_ID": "wiibble_sim_01",
        "RATE_HZ": 50,
        "COP_X_RANGE": (-216, 216),
        "COP_Y_RANGE": (-114, 114),
        "TOTAL_WT_RANGE": (0, 150),
        "QUAD_KG_RANGE": (0, 75),
    }
    exec(chunk, namespace)  # noqa: S102
    return namespace["ANNOUNCE"]


@pytest.mark.skipif(not THRIVE_SIM_PATH.is_file(), reason="THRIVE repo not present")
def test_announce_channel_schema_matches_thrive_fixture():
    """Compare channel/signal structure to THRIVE wiibble.py ANNOUNCE dict."""
    sim = _load_thrive_sim_announce()
    bridge = build_announce("2.1.0", node_id="wiibble_01")

    for key in ("channels", "signals_offered", "commands", "settings"):
        assert json.dumps(bridge[key], sort_keys=True) == json.dumps(
            sim[key], sort_keys=True
        ), f"Mismatch in announce[{key!r}]"
