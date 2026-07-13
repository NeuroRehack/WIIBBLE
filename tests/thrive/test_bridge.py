"""Tests for MQTT publish throttling."""

import time

from wiibble.thrive.bridge import PublishThrottle


def test_throttle_limits_to_target_rate():
    throttle = PublishThrottle(rate_hz=50.0)
    t0 = 1000.0
    assert throttle.should_publish(t0) is True
    assert throttle.should_publish(t0 + 0.01) is False
    assert throttle.should_publish(t0 + 0.02) is True


def test_throttle_100hz_input_yields_50hz_output():
    """Simulate 100 Hz frame arrivals; only ~half should pass."""
    throttle = PublishThrottle(rate_hz=50.0)
    start = time.monotonic()
    published = 0
    for i in range(100):
        if throttle.should_publish(start + i * 0.01):
            published += 1
    assert 48 <= published <= 52


def test_throttle_reset_allows_immediate_publish():
    throttle = PublishThrottle(rate_hz=50.0)
    t0 = 0.0
    assert throttle.should_publish(t0) is True
    assert throttle.should_publish(t0 + 0.005) is False
    throttle.reset()
    assert throttle.should_publish(t0 + 0.005) is True
