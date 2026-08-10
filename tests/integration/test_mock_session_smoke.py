"""Integration smoke tests for WIIBBLE startup."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
STARTUP_MARKERS = ("Starting WIIBBLE", "Using MockHIDDevice", "mock=True")


@pytest.mark.integration
def test_mock_session_emits_startup_marker() -> None:
    """Launch ``wiibble --mock`` and confirm a known startup log line appears."""
    proc = subprocess.Popen(
        [sys.executable, "-m", "wiibble", "--mock", "--mock-scenario", "sway"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    output = ""
    try:
        deadline = time.monotonic() + 12.0
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                break
            chunk = proc.stdout.read(256) if proc.stdout else ""
            if chunk:
                output += chunk
                if any(marker in output for marker in STARTUP_MARKERS):
                    return
            time.sleep(0.1)
        pytest.fail(
            f"Startup marker not seen within timeout. Output so far:\n{output[:500]}"
        )
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
