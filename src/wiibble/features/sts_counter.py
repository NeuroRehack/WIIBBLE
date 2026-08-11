"""Sit-to-stand rep counter state machine.

Detects seated ↔ standing transitions from total board weight using
hysteresis thresholds expressed as a percentage of calibrated body weight.
A rep is counted when the stand threshold is held for the minimum stand time.
The patient must return to a confirmed seated state before the next rep can
register.
"""

from __future__ import annotations

import logging
import time
from enum import StrEnum

from wiibble.utils.constants import STS_REP_FLASH_SECONDS
from wiibble.utils.state import AppState, Settings

log = logging.getLogger(__name__)

STS_GAUGE_MAX_PCT = 200.0  # total-body-weight % at which a mirrored flank reaches the bar edge


class StsState(StrEnum):
    """High-level posture states for the STS counter."""

    SEATED = "seated"
    STANDING_PENDING = "standing_pending"
    STANDING = "standing"
    SEATED_PENDING = "seated_pending"


def stand_threshold_kg(body_weight_kg: float, stand_pct: float) -> float:
    """Return the kg threshold above which the patient is considered standing.

    Args:
        body_weight_kg: Calibrated reference body weight.
        stand_pct: Stand threshold as a percentage of body weight.

    Returns:
        Absolute weight threshold in kg.
    """
    return body_weight_kg * stand_pct / 100.0


def sit_threshold_kg(body_weight_kg: float, sit_pct: float) -> float:
    """Return the kg threshold below which the patient is considered seated.

    Args:
        body_weight_kg: Calibrated reference body weight.
        sit_pct: Sit threshold as a percentage of body weight.

    Returns:
        Absolute weight threshold in kg.
    """
    return body_weight_kg * sit_pct / 100.0


def weight_pct_of_body(curr_weight_kg: float, body_weight_kg: float) -> float:
    """Express current weight as a percentage of calibrated body weight.

    Args:
        curr_weight_kg: Live total weight on the board.
        body_weight_kg: Calibrated reference body weight.

    Returns:
        Percentage of body weight, or 0 when body weight is unknown.
    """
    if body_weight_kg <= 0:
        return 0.0
    return 100.0 * curr_weight_kg / body_weight_kg


def format_sts_state_label(state: str) -> str:
    """Return a human-readable label for an STS state value.

    Args:
        state: One of the :class:`StsState` string values.

    Returns:
        Title-case label suitable for the settings live-status line.
    """
    labels = {
        StsState.SEATED.value: "Seated",
        StsState.STANDING_PENDING.value: "Standing…",
        StsState.STANDING.value: "Standing",
        StsState.SEATED_PENDING.value: "Sitting…",
    }
    return labels.get(state, "Unknown")


def sts_flank_offset_fraction(pct: float) -> float:
    """Return mirrored flank position as a fraction of half-bar width (0–1).

    Both flanks fill outward from the true centre (0% body weight) in
    proportion to the weight magnitude, so a higher percentage always
    pushes the marker further from centre and never back toward it.

    ``pct`` is a *total* body-weight percentage (both feet combined), but
    each flank of the stats bar is filled by a single foot's share of that
    total (see ``pl``/``pr`` in ``session.py``). Assuming an even left/right
    split, one foot carries half the total load, so the scale is doubled
    (``STS_GAUGE_MAX_PCT``) to keep threshold markers aligned with where the
    live fill actually reaches — e.g. a 100% total-weight value lands
    halfway along the flank, matching a normal two-footed stand.

    Args:
        pct: Body-weight percentage (e.g. threshold or live weight %).

    Returns:
        Fraction of one flank width from centre, clamped to 1.0.
    """
    return min(1.0, max(0.0, pct) / STS_GAUGE_MAX_PCT)


def _register_sts_rep(app_state: AppState) -> None:
    """Increment the STS rep count and mark the counter disarmed until seated.

    Args:
        app_state: Runtime session state.
    """
    app_state.sts_rep_count += 1
    app_state.sts_disarmed = True
    app_state.sts_rep_flash_until = time.time() + STS_REP_FLASH_SECONDS
    log.info("STS rep registered (count=%d)", app_state.sts_rep_count)


def _confirm_standing(app_state: AppState) -> None:
    """Enter the standing state and count a rep when the counter is armed.

    Args:
        app_state: Runtime session state.
    """
    app_state.sts_state = StsState.STANDING.value
    app_state.sts_stand_dwell = 0.0
    if not app_state.sts_disarmed:
        _register_sts_rep(app_state)


def _confirm_seated(app_state: AppState) -> None:
    """Enter the seated state and re-arm the counter for the next rep.

    Args:
        app_state: Runtime session state.
    """
    app_state.sts_state = StsState.SEATED.value
    app_state.sts_sit_dwell = 0.0
    app_state.sts_disarmed = False


def update_sts_counter(
    app_state: AppState,
    settings: Settings,
    curr_weight_kg: float,
    *,
    dt: float | None = None,
) -> None:
    """Advance the STS state machine and increment the rep count on stand.

    Args:
        app_state: Runtime session state (rep count and internal STS fields).
        settings: User settings including thresholds and enable flag.
        curr_weight_kg: Smoothed total weight on the board this frame.
        dt: Elapsed seconds since the last update; computed when omitted.
    """
    if not settings.sts_enabled:
        return
    if settings.body_weight_kg <= 0:
        return

    app_state.sts_last_weight_kg = curr_weight_kg

    if dt is None:
        now = time.perf_counter()
        dt = 0.0 if app_state.sts_last_tick <= 0 else now - app_state.sts_last_tick
        app_state.sts_last_tick = now

    stand_kg = stand_threshold_kg(
        settings.body_weight_kg, settings.sts_stand_threshold_pct
    )
    sit_kg = sit_threshold_kg(settings.body_weight_kg, settings.sts_sit_threshold_pct)

    state = StsState(app_state.sts_state)

    if state == StsState.SEATED:
        if curr_weight_kg >= stand_kg:
            app_state.sts_state = StsState.STANDING_PENDING.value
            app_state.sts_stand_dwell = dt
            if app_state.sts_stand_dwell >= settings.sts_min_stand_seconds:
                _confirm_standing(app_state)
    elif state == StsState.STANDING_PENDING:
        if curr_weight_kg < sit_kg:
            app_state.sts_state = StsState.SEATED.value
            app_state.sts_stand_dwell = 0.0
        elif curr_weight_kg >= stand_kg:
            app_state.sts_stand_dwell += dt
            if app_state.sts_stand_dwell >= settings.sts_min_stand_seconds:
                _confirm_standing(app_state)
        else:
            app_state.sts_stand_dwell = 0.0
    elif state == StsState.STANDING:
        if curr_weight_kg <= sit_kg:
            app_state.sts_state = StsState.SEATED_PENDING.value
            app_state.sts_sit_dwell = dt
            if app_state.sts_sit_dwell >= settings.sts_min_sit_seconds:
                _confirm_seated(app_state)
    elif state == StsState.SEATED_PENDING:
        if curr_weight_kg >= stand_kg:
            app_state.sts_state = StsState.STANDING.value
            app_state.sts_sit_dwell = 0.0
        elif curr_weight_kg <= sit_kg:
            app_state.sts_sit_dwell += dt
            if app_state.sts_sit_dwell >= settings.sts_min_sit_seconds:
                _confirm_seated(app_state)
        else:
            app_state.sts_sit_dwell = 0.0
