# tests/test_target_dwell.py
# Unit tests for target dwell hit-counter state machine.

from wiibble.ui.ui import update_target_dwell
from wiibble.utils.constants import TARGET_DWELL_DEFAULT
from wiibble.utils.state import AppState


class DummySettings:
    target_dwell_seconds = TARGET_DWELL_DEFAULT


def _step(app_state, settings, hit_by_index: dict[int, bool], dt: float) -> None:
    update_target_dwell(app_state, settings, hit_by_index, dt=dt)


class TestUpdateTargetDwell:
    def test_dwell_below_threshold_does_not_increment(self):
        app_state = AppState()
        settings = DummySettings()
        settings.target_dwell_seconds = 1

        _step(app_state, settings, {0: True}, 0.5)

        assert app_state.target_hit_count == 0

    def test_dwell_at_threshold_increments_once(self):
        app_state = AppState()
        settings = DummySettings()
        settings.target_dwell_seconds = 1

        _step(app_state, settings, {0: True}, 1.0)

        assert app_state.target_hit_count == 1
        assert 0 in app_state._target_dwell_disarmed

    def test_staying_after_increment_does_not_chain(self):
        app_state = AppState()
        settings = DummySettings()
        settings.target_dwell_seconds = 1

        _step(app_state, settings, {0: True}, 1.0)
        _step(app_state, settings, {0: True}, 1.0)

        assert app_state.target_hit_count == 1

    def test_leave_and_reenter_allows_second_count(self):
        app_state = AppState()
        settings = DummySettings()
        settings.target_dwell_seconds = 1

        _step(app_state, settings, {0: True}, 1.0)
        _step(app_state, settings, {0: False}, 0.1)
        _step(app_state, settings, {0: True}, 1.0)

        assert app_state.target_hit_count == 2

    def test_leaving_mid_dwell_resets_elapsed(self):
        app_state = AppState()
        settings = DummySettings()
        settings.target_dwell_seconds = 1

        _step(app_state, settings, {0: True}, 0.5)
        _step(app_state, settings, {0: False}, 0.1)
        _step(app_state, settings, {0: True}, 0.5)

        assert app_state.target_hit_count == 0

    def test_overlap_counts_other_target_while_still_in_counted_one(self):
        app_state = AppState()
        settings = DummySettings()
        settings.target_dwell_seconds = 1

        _step(app_state, settings, {0: True}, 1.0)
        assert app_state.target_hit_count == 1

        _step(app_state, settings, {0: True, 1: True}, 1.0)
        assert app_state.target_hit_count == 2

    def test_overlap_requires_leaving_counted_target_before_recount(self):
        app_state = AppState()
        settings = DummySettings()
        settings.target_dwell_seconds = 1

        _step(app_state, settings, {0: True, 1: True}, 1.0)
        assert app_state.target_hit_count == 2

        _step(app_state, settings, {1: True}, 1.0)
        assert app_state.target_hit_count == 2

        _step(app_state, settings, {1: True}, 1.0)
        assert app_state.target_hit_count == 2

        _step(app_state, settings, {1: False}, 0.1)
        _step(app_state, settings, {1: True}, 1.0)
        assert app_state.target_hit_count == 3

    def test_zero_dwell_increments_immediately(self):
        app_state = AppState()
        settings = DummySettings()
        settings.target_dwell_seconds = 0

        _step(app_state, settings, {0: True}, 0.0)

        assert app_state.target_hit_count == 1

    def test_reset_target_counter_clears_state(self):
        app_state = AppState()
        settings = DummySettings()
        settings.target_dwell_seconds = 1

        _step(app_state, settings, {0: True}, 1.0)
        app_state.reset_target_counter()

        assert app_state.target_hit_count == 0
        assert app_state._target_dwell_elapsed == {}
        assert app_state._target_dwell_disarmed == set()
        assert app_state._target_dwell_last_tick == 0.0


class TestTargetHitHelper:
    def test_circle_hit_inside(self):
        from wiibble.ui.ui import _target_hit_at_point

        target = {"center": (0.0, 0.0), "radius": 10.0}
        assert _target_hit_at_point(target, 100, 100, 100, 100, 1.0, False, False)

    def test_circle_hit_outside(self):
        from wiibble.ui.ui import _target_hit_at_point

        target = {"center": (0.0, 0.0), "radius": 10.0}
        assert not _target_hit_at_point(target, 200, 200, 100, 100, 1.0, False, False)
