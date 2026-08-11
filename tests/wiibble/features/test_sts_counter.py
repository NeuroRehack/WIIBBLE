"""Unit tests for sit-to-stand rep counter state machine."""

from __future__ import annotations

from dataclasses import dataclass

from wiibble.features.sts_counter import (
    StsState,
    format_sts_state_label,
    sts_flank_offset_fraction,
    update_sts_counter,
    weight_pct_of_body,
)
from wiibble.utils.constants import (
    STS_MIN_SIT_SECONDS_DEFAULT,
    STS_MIN_STAND_SECONDS_DEFAULT,
    STS_SIT_THRESHOLD_PCT_DEFAULT,
    STS_STAND_THRESHOLD_PCT_DEFAULT,
)
from wiibble.utils.state import AppState


@dataclass
class DummySettings:
    """Minimal settings stub for STS counter tests."""

    sts_enabled: bool = True
    body_weight_kg: float = 70.0
    sts_stand_threshold_pct: float = STS_STAND_THRESHOLD_PCT_DEFAULT
    sts_sit_threshold_pct: float = STS_SIT_THRESHOLD_PCT_DEFAULT
    sts_min_stand_seconds: float = STS_MIN_STAND_SECONDS_DEFAULT
    sts_min_sit_seconds: float = STS_MIN_SIT_SECONDS_DEFAULT


def _stand_weight(settings: DummySettings) -> float:
    return settings.body_weight_kg * settings.sts_stand_threshold_pct / 100.0 + 1.0


def _sit_weight(settings: DummySettings) -> float:
    return settings.body_weight_kg * settings.sts_sit_threshold_pct / 100.0 - 1.0


def _below_sit_weight(settings: DummySettings) -> float:
    return settings.body_weight_kg * settings.sts_sit_threshold_pct / 100.0 - 5.0


def _step(
    app_state: AppState,
    settings: DummySettings,
    weight_kg: float,
    dt: float,
) -> None:
    update_sts_counter(app_state, settings, weight_kg, dt=dt)


class TestWeightPctOfBody:
    def test_returns_percentage(self) -> None:
        assert weight_pct_of_body(35.0, 70.0) == 50.0

    def test_zero_body_weight_returns_zero(self) -> None:
        assert weight_pct_of_body(50.0, 0.0) == 0.0


class TestFormatStsStateLabel:
    def test_known_states(self) -> None:
        assert format_sts_state_label(StsState.SEATED.value) == "Seated"
        assert format_sts_state_label(StsState.STANDING.value) == "Standing"


class TestStsFlankOffsetFraction:
    def test_zero_is_zero(self) -> None:
        assert sts_flank_offset_fraction(0.0) == 0.0

    def test_full_body_weight_is_half_flank(self) -> None:
        """100% total body weight lands halfway, matching an even two-foot split."""
        assert sts_flank_offset_fraction(100.0) == 0.5

    def test_full_scale_is_full_flank(self) -> None:
        assert sts_flank_offset_fraction(200.0) == 1.0

    def test_partial_value_is_proportional(self) -> None:
        assert sts_flank_offset_fraction(60.0) == 0.3

    def test_above_flank_range_is_clamped(self) -> None:
        assert sts_flank_offset_fraction(250.0) == 1.0

    def test_no_fold_back_around_old_centre(self) -> None:
        """Regression test: values straddling the old 50% anchor must not collide."""
        assert sts_flank_offset_fraction(40.0) != sts_flank_offset_fraction(60.0)

    def test_monotonic_across_sit_stand_range(self) -> None:
        """Offsets must strictly increase across the valid sit/stand threshold range."""
        assert (
            sts_flank_offset_fraction(10.0)
            < sts_flank_offset_fraction(55.0)
            < sts_flank_offset_fraction(85.0)
        )

    def test_stand_marker_stays_within_reach_of_even_split_fill(self) -> None:
        """A per-foot fill fraction from an evenly split standing load must be able
        to exceed the stand marker, so the bar visually reflects a Standing state.
        """
        total_pct = 103.0
        per_foot_fill_fraction = (total_pct / 100.0) / 2.0
        stand_pct = 60.0
        assert per_foot_fill_fraction > sts_flank_offset_fraction(stand_pct)


class TestUpdateStsCounter:
    def test_disabled_does_not_update(self) -> None:
        app_state = AppState()
        settings = DummySettings(sts_enabled=False)
        _step(app_state, settings, _stand_weight(settings), 1.0)
        assert app_state.sts_rep_count == 0

    def test_stand_confirmed_increments_rep(self) -> None:
        app_state = AppState()
        settings = DummySettings()
        stand = _stand_weight(settings)

        _step(app_state, settings, stand, settings.sts_min_stand_seconds)

        assert app_state.sts_rep_count == 1
        assert app_state.sts_state == StsState.STANDING.value
        assert app_state.sts_disarmed is True

    def test_sitting_after_rep_does_not_increment(self) -> None:
        app_state = AppState()
        settings = DummySettings()
        stand = _stand_weight(settings)
        sit = _sit_weight(settings)

        _step(app_state, settings, stand, settings.sts_min_stand_seconds)
        _step(app_state, settings, sit, settings.sts_min_sit_seconds)

        assert app_state.sts_rep_count == 1
        assert app_state.sts_state == StsState.SEATED.value
        assert app_state.sts_disarmed is False

    def test_staying_standing_after_rep_does_not_chain(self) -> None:
        app_state = AppState()
        settings = DummySettings()
        stand = _stand_weight(settings)

        _step(app_state, settings, stand, settings.sts_min_stand_seconds)
        _step(app_state, settings, stand, 1.0)

        assert app_state.sts_rep_count == 1

    def test_second_rep_requires_sit_then_stand(self) -> None:
        app_state = AppState()
        settings = DummySettings()
        stand = _stand_weight(settings)
        sit = _sit_weight(settings)

        _step(app_state, settings, stand, settings.sts_min_stand_seconds)
        _step(app_state, settings, sit, settings.sts_min_sit_seconds)
        _step(app_state, settings, stand, settings.sts_min_stand_seconds)

        assert app_state.sts_rep_count == 2

    def test_false_start_during_stand_pending_resets(self) -> None:
        app_state = AppState()
        settings = DummySettings()
        stand = _stand_weight(settings)

        _step(app_state, settings, stand, settings.sts_min_stand_seconds * 0.5)
        _step(app_state, settings, _below_sit_weight(settings), 0.1)

        assert app_state.sts_state == StsState.SEATED.value
        assert app_state.sts_rep_count == 0

    def test_bounce_during_sit_pending_does_not_recount(self) -> None:
        app_state = AppState()
        settings = DummySettings()
        stand = _stand_weight(settings)
        sit = _sit_weight(settings)

        _step(app_state, settings, stand, settings.sts_min_stand_seconds)
        assert app_state.sts_rep_count == 1
        _step(app_state, settings, sit, settings.sts_min_sit_seconds * 0.5)
        _step(app_state, settings, stand, 0.1)

        assert app_state.sts_state == StsState.STANDING.value
        assert app_state.sts_rep_count == 1

    def test_insufficient_stand_dwell_does_not_confirm(self) -> None:
        app_state = AppState()
        settings = DummySettings()
        stand = _stand_weight(settings)

        _step(app_state, settings, stand, settings.sts_min_stand_seconds * 0.5)

        assert app_state.sts_state == StsState.STANDING_PENDING.value
        assert app_state.sts_rep_count == 0

    def test_reset_sts_counter_clears_state(self) -> None:
        app_state = AppState()
        settings = DummySettings()
        stand = _stand_weight(settings)

        _step(app_state, settings, stand, settings.sts_min_stand_seconds)
        app_state.reset_sts_counter()

        assert app_state.sts_rep_count == 0
        assert app_state.sts_state == StsState.SEATED.value
        assert app_state.sts_stand_dwell == 0.0
        assert app_state.sts_sit_dwell == 0.0
        assert app_state.sts_disarmed is False
