"""CoP feature extraction pipeline for WIIBBLE recordings.

End-to-end pipeline:
    load_recording() → to_cop_array() → Stabilogram.from_array() → compute_all_features()

WBB geometry source:
    Leach et al. (2014) Sensors 14:18244-18267, doi:10.3390/s141018244, Figure 3.
    X = 433 mm (ML), Y = 238 mm (AP).

CoP formula source:
    Leach et al. (2014), Equation 1 (citing Winter 2004):
        CoP_ML = (X/2) × (F_R - F_L) / F_total
        CoP_AP = (Y/2) × (F_T - F_B) / F_total

    In WIIBBLE terms (x_kg = F_R − F_L, y_kg = F_T − F_B):
        CoP_ML_cm = WBB_SENSOR_DIST_ML_CM × x_kg / total_weight_kg
        CoP_AP_cm = WBB_SENSOR_DIST_AP_CM × y_kg / total_weight_kg

Recording filter note:
    WIIBBLE recordings always contain raw (unfiltered) force-deviation values.
    The ``ui_filter_window`` metadata comment records what smoothing was applied
    to the display cursor during the session — it does NOT describe the data.
    The Stabilogram's own Butterworth filter (0–10 Hz, order 4) is the only
    filter applied to the analysis signal.
"""

import logging
from pathlib import Path

import numpy as np

from code_descriptors_postural_control.descriptors import compute_all_features
from code_descriptors_postural_control.stabilogram.stato import Stabilogram
from wiibble.utils.constants import WBB_SENSOR_DIST_AP_CM, WBB_SENSOR_DIST_ML_CM

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CSV loading
# ---------------------------------------------------------------------------


def load_recording(path: str) -> tuple:
    """Read a WIIBBLE CSV and return ``(data, metadata)``.

    The CSV may start with comment lines of the form ``# key=value``.
    These are parsed into *metadata*.  The remainder is standard CSV with a
    header row ``time (s), x (kg), y (kg)``.

    Returns
    -------
    data : np.ndarray, shape (N, 3)
        Columns: ``[time_s, x_kg, y_kg]``
    metadata : dict[str, str]
        Key/value pairs extracted from comment lines.  Common keys:
        ``total_weight_kg``, ``filter_window``.
    """
    metadata: dict = {}
    rows: list = []

    with open(path, newline="") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                # e.g.  "# total_weight_kg=65.1200"
                content = stripped[1:].strip()
                key, _, val = content.partition("=")
                if val:
                    metadata[key.strip()] = val.strip()
                continue
            if stripped.startswith("time"):
                # header row — skip
                continue
            parts = stripped.split(",")
            if len(parts) == 3:
                try:
                    rows.append([float(p) for p in parts])
                except ValueError:
                    log.warning("Skipping unparseable row in %s: %s", path, stripped)

    if not rows:
        raise ValueError(f"No data rows found in {path}")

    data = np.array(rows, dtype=float)
    return data, metadata


# ---------------------------------------------------------------------------
# CoP conversion
# ---------------------------------------------------------------------------


def to_cop_array(data: np.ndarray, total_weight_kg: float) -> np.ndarray:
    """Convert WIIBBLE force deviations to Centre of Pressure in centimetres.

    WIIBBLE stores:
        x_kg : (right − left) corner sums in kg  → mediolateral (ML) axis
        y_kg : (top − bottom) corner sums in kg  → anteroposterior (AP) axis

    CoP formula (Leach et al. 2014, Eq. 1):
        CoP_ML_cm = WBB_SENSOR_DIST_ML_CM × x_kg / total_weight_kg
        CoP_AP_cm = WBB_SENSOR_DIST_AP_CM × y_kg / total_weight_kg

    Parameters
    ----------
    data : np.ndarray, shape (N, 3)
        Output of :func:`load_recording` — columns ``[time_s, x_kg, y_kg]``.
    total_weight_kg : float
        Subject body weight measured during calibration.

    Returns
    -------
    np.ndarray, shape (N, 3)
        Columns: ``[time_s, ML_cm, AP_cm]``.  Input for
        ``Stabilogram.from_array()``.
    """
    if total_weight_kg <= 0:
        raise ValueError(f"total_weight_kg must be positive, got {total_weight_kg}")

    time_s = data[:, 0]
    x_kg = data[:, 1]
    y_kg = data[:, 2]

    ml_cm = WBB_SENSOR_DIST_ML_CM * x_kg / total_weight_kg
    ap_cm = WBB_SENSOR_DIST_AP_CM * y_kg / total_weight_kg

    return np.column_stack([time_s, ml_cm, ap_cm])


# ---------------------------------------------------------------------------
# End-to-end analysis
# ---------------------------------------------------------------------------


def analyse_recording(path: str, total_weight_kg: float = None) -> dict:
    """Full pipeline: WIIBBLE CSV → CoP → Stabilogram → feature dictionary.

    Parameters
    ----------
    path : str
        Path to a WIIBBLE recording CSV.
    total_weight_kg : float, optional
        Override the body weight.  If ``None``, the value is read from the
        ``# total_weight_kg=`` comment in the CSV header.  Recordings made
        before this feature was added will not have this metadata — either
        delete and re-record, or pass ``total_weight_kg`` explicitly.

    Returns
    -------
    dict
        ~80–90 posturographic features from
        ``code_descriptors_postural_control.descriptors.compute_all_features``
        plus provenance keys:
        ``source_file``, ``total_weight_kg``, ``ui_filter_window``,
        ``n_samples_raw``, ``duration_s``.

    Raises
    ------
    ValueError
        If body weight cannot be determined.
    """
    data, metadata = load_recording(path)

    # ---- resolve body weight ------------------------------------------------
    weight_kg = total_weight_kg
    if weight_kg is None:
        raw = metadata.get("total_weight_kg")
        if raw is None:
            raise ValueError(
                f"total_weight_kg not found in '{path}' and not provided as an argument. "
                "Re-record with the current WIIBBLE version, or pass total_weight_kg explicitly."
            )
        weight_kg = float(raw)

    # ---- ui filter window (provenance only — data is always raw) -----------
    fw = int(metadata.get("ui_filter_window", metadata.get("filter_window", 1)))

    # ---- minimum duration check (30 s recommended for stable estimates) -----
    duration_s = float(data[-1, 0] - data[0, 0])
    if duration_s < 20.0:
        log.warning(
            "Recording '%s' is only %.1f s long. "
            "At least 30 s is recommended for reliable posturographic estimates.",
            Path(path).name,
            duration_s,
        )

    # ---- CoP conversion -----------------------------------------------------
    cop_array = to_cop_array(data, weight_kg)

    # ---- Stabilogram --------------------------------------------------------
    # from_array with 3 columns (time, ML, AP) triggers SWARII resampling to
    # 25 Hz, followed by Butterworth bandpass (0–10 Hz, order 4).
    stabilogram = Stabilogram()
    stabilogram.from_array(cop_array)

    # ---- Feature extraction -------------------------------------------------
    features = compute_all_features(stabilogram)

    # ---- Provenance ---------------------------------------------------------
    features["source_file"] = Path(path).name
    features["total_weight_kg"] = weight_kg
    features["ui_filter_window"] = fw
    features["n_samples_raw"] = len(data)
    features["duration_s"] = duration_s

    log.info(
        "Analysed '%s': %d features, %.1f s, %.0f Hz raw → 25 Hz resampled",
        Path(path).name,
        len(features),
        duration_s,
        len(data) / duration_s if duration_s > 0 else 0,
    )
    return features
