"""CSV recording utilities for WIIBBLE.

This module is responsible for serializing recording buffers to timestamped
CSV files under the recordings directory.
"""

# recording.py
# CSV recording output — extracted from app.py to enable isolated unit testing.
import csv
import datetime
import logging
import os

log = logging.getLogger(__name__)


def _save_recording_csv(
    record_buffer, total_weight_kg: float = None, ui_filter_window: int = 1
) -> str:
    """Save the provided recording buffer to a timestamped CSV file.

    The recorded values are always raw (unfiltered) corner force deviations.
    ``ui_filter_window`` is stored as provenance metadata only — it describes
    the smoothing that was applied to the *display* cursor, not to the data.

    Metadata is written as comment lines (prefixed with ``#``) before the CSV
    header so it can be recovered by the analysis pipeline without breaking
    standard CSV readers that skip unknown lines.

    Returns the absolute path of the written file.
    """
    out_dir = os.path.join(os.getcwd(), "recordings")
    os.makedirs(out_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"recording_{timestamp}.csv"
    path = os.path.join(out_dir, filename)
    with open(path, "w", newline="") as f:
        # Metadata comments — parsed by analysis.load_recording()
        if total_weight_kg is not None:
            f.write(f"# total_weight_kg={total_weight_kg:.4f}\n")
        f.write(f"# ui_filter_window={ui_filter_window}\n")
        writer = csv.writer(f)
        writer.writerow(["time (s)", "x (kg)", "y (kg)"])
        for row in record_buffer:
            writer.writerow([f"{row[0]:.3f}", f"{row[1]:.3f}", f"{row[2]:.3f}"])
    log.info("Recording saved to %s", path)
    return path
