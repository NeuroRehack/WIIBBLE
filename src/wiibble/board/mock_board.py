"""Mock Wii Balance Board hardware support.

This module provides a fake HID device implementation that simulates Wii
Balance Board weight data in configurable scenarios. It is used for local
mock mode so the UI and calibration flow can be exercised without hardware.
"""

import logging
import math
import random
import time

from wiibble.utils.constants import SCALE_FACTOR_DEFAULT

log = logging.getLogger(__name__)

# Real Wii Balance Board HID report rate
_BOARD_REPORT_INTERVAL = 1.0 / 100  # 100 Hz


class MockHIDDevice:
    """
    Drop-in replacement for hid.device() simulating Wii Balance Board data.

    Phase model:
      "tare"           - Board is empty. Returns ~0 kg per sensor so that
                         wait_for_tare() and tare() record a clean zero baseline.
                         This is the initial state on open().

      "step_on_stable" - User has stepped on. Returns stable ~18 kg per
                         sensor until enter_running_mode() is called.

      "normal"         - Running mode. Returns scenario-based sway simulation.

    IMPORTANT: trigger_step_on() must be called from main() immediately after
    tare() completes and before sensitivity_calibration() is called.
    This mirrors the real user flow: board empty -> tare -> step on -> calibrate.

    Do NOT use read-count based phase transitions -- measure_weight() calls
    read() 10 times per measurement in a tight loop, so counts burn through
    instantly and phases change at the wrong time.
    """

    def __init__(self, scenario="sway"):
        """Initialize the mock device with the selected scenario and starting phase."""
        self.scenario = scenario
        self._phase = "tare"
        self._stable_until = None
        self.start_time = time.time()
        self._scenario_params = {}
        self._nonblocking = False
        self._last_data_time = None
        self._scale_factor = SCALE_FACTOR_DEFAULT
        self._step_on_kg = None
        self._set_scenario(scenario)

    @classmethod
    def from_scenario(cls, scenario):
        """Create a mock device configured for the given scenario."""
        return cls(scenario)

    def _set_scenario(self, scenario):
        """Configure the simulated weight pattern for a named scenario."""
        if scenario == "still":
            self._scenario_params = {
                "base": [18.0, 18.0, 18.0, 18.0],
                "noise": 0.03,
                "sway": 0.0,
            }
        elif scenario == "lean_left":
            self._scenario_params = {
                "base": [12.0, 12.0, 24.0, 24.0],
                "noise": 0.1,
                "sway": 0.5,
            }
        elif scenario == "lean_right":
            self._scenario_params = {
                "base": [24.0, 24.0, 12.0, 12.0],
                "noise": 0.1,
                "sway": 0.5,
            }
        elif scenario == "hands":
            self._scenario_params = {
                "base": [1.5, 1.5, 1.5, 1.5],
                "noise": 0.03,
                "sway": 0.05,
            }
        elif scenario == "step_on_off":
            # Parameters for step on/off: base weight, noise, cycle duration
            self._scenario_params = {
                "base": [18.0, 18.0, 18.0, 18.0],
                "noise": 0.05,
                "step_weight": 18.0,  # weight per sensor when on
                "off_weight": 0.0,  # weight per sensor when off
                "step_duration": 2.0,  # seconds on
                "off_duration": 2.0,  # seconds off
            }
        elif scenario == "calibration":
            # Stable load for testing on-demand board calibration without hardware
            self._scenario_params = {
                "base": [18.0, 18.0, 18.0, 18.0],
                "noise": 0.03,
                "sway": 0.0,
            }
        else:  # "sway" default
            self._scenario_params = {
                "base": [18.0, 18.0, 18.0, 18.0],
                "noise": 0.15,
                "sway": 1.0,
            }

    def open(self, vendor_id, product_id):
        """Initialize the mock device and reset its calibration phase."""
        self._phase = "tare"
        self._stable_until = None
        self.start_time = time.time()
        self._nonblocking = False
        self._last_data_time = None

    def set_nonblocking(self, nonblocking):
        """Mirror hid.device.set_nonblocking.

        When 1, read() returns [] if no new report.
        """
        self._nonblocking = bool(nonblocking)

    def close(self):
        """Close the mock device and release any simulated resources."""
        log.debug("Mock HID device closed.")

    def set_scale_factor(self, scale_factor: float) -> None:
        """Set the HID kg/raw factor used when encoding simulated reports."""
        self._scale_factor = scale_factor

    def enter_running_mode(self):
        """Leave tare phase and simulate the configured scenario (post startup tare)."""
        self._phase = "normal"
        self.start_time = time.time()

    def reset_calibration_phase(self):
        """Return to empty-board phase before on-demand calibration."""
        self._phase = "tare"
        self._stable_until = None
        self._step_on_kg = None

    def trigger_step_on(self):
        """
        Call before sensitivity_calibration() so the mock simulates stepping on.

        Enters step_on_stable until enter_running_mode() is called after calibration.
        """
        if self._phase == "tare":
            self._step_on_kg = list(self._scenario_params["base"])
            self._phase = "step_on_stable"
            self._stable_until = None
            self.start_time = time.time()

    def trigger_reference_load(self, reference_kg: float) -> None:
        """Simulate placing a known reference mass evenly on all four sensors."""
        if self._phase == "tare":
            per_sensor = reference_kg / 4.0
            self._step_on_kg = [per_sensor, per_sensor, per_sensor, per_sensor]
            self._phase = "step_on_stable"
            self._stable_until = None
            self.start_time = time.time()

    def read(self, size):
        """Return a raw HID byte array for the current simulated board state.

        In non-blocking mode, returns [] if called faster than the real board's
        100 Hz report rate, matching hid.device behaviour.
        """
        if (
            self._nonblocking
            and self._last_data_time is not None
            and time.time() - self._last_data_time < _BOARD_REPORT_INTERVAL
        ):
            return []
        self._last_data_time = time.time()

        kg_vals = self._get_kg_values()
        data = [0] * size
        indices = [3, 5, 7, 9]  # top_right, bottom_right, top_left, bottom_left
        for idx, kg in zip(indices, kg_vals, strict=False):
            raw = max(0.0, kg) / self._scale_factor
            int_part = int(raw)
            frac_part = int((raw - int_part) * 255)
            data[idx] = int_part
            data[idx + 1] = frac_part

        # Slow down calibration phases so the clinician can read the screen.
        # measure_weight() calls read() 10 times per measurement, so a 50ms
        # sleep here gives ~0.5s per weight sample — natural pacing.
        # No sleep in normal mode to keep the main loop responsive at 60fps.
        if self._phase in ("tare", "step_on_stable"):
            time.sleep(0.02)

        return data

    def _get_kg_values(self):
        """Return the current simulated kg values for each board corner."""
        if self._phase == "tare":
            return [0.0, 0.0, 0.0, 0.0]

        if self._phase == "step_on_stable":
            base = self._step_on_kg or self._scenario_params["base"]
            return [v + random.gauss(0, 0.02) for v in base]

        return self._simulate_normal()

    def _simulate_normal(self):
        """Simulate a normal running scenario, including sway and noise."""
        t = time.time() - self.start_time
        p = self._scenario_params
        base = p["base"]
        noise = p["noise"]

        if self.scenario == "still" or self.scenario == "calibration":
            return [v + random.gauss(0, noise) for v in base]

        elif self.scenario == "lean_left":
            drift = math.sin(t / 3.0) * 1.5
            return [
                base[0] + drift + random.gauss(0, noise),
                base[1] + drift + random.gauss(0, noise),
                base[2] - drift + random.gauss(0, noise),
                base[3] - drift + random.gauss(0, noise),
            ]

        elif self.scenario == "lean_right":
            drift = math.sin(t / 3.0) * 1.5
            return [
                base[0] - drift + random.gauss(0, noise),
                base[1] - drift + random.gauss(0, noise),
                base[2] + drift + random.gauss(0, noise),
                base[3] + drift + random.gauss(0, noise),
            ]

        elif self.scenario == "hands":
            return [v + random.gauss(0, noise) for v in base]

        elif self.scenario == "step_on_off":
            # Cycle: step on for step_duration, then off for off_duration
            cycle = p["step_duration"] + p["off_duration"]
            t_mod = t % cycle
            weight = p["step_weight"] if t_mod < p["step_duration"] else p["off_weight"]
            return [weight + random.gauss(0, noise) for _ in range(4)]

        else:  # sway
            sway = p["sway"]
            amp = sway * 2.5
            lateral = math.sin(t / 2.0) * amp
            fore_aft = math.sin(t / 3.5) * amp * 0.6
            n = random.gauss(0, noise)
            return [
                base[0] + lateral + fore_aft + n,
                base[1] + lateral - fore_aft + n,
                base[2] - lateral + fore_aft + n,
                base[3] - lateral - fore_aft + n,
            ]
