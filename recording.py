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


def _save_recording_csv(record_buffer):
    """Save the provided recording buffer to a timestamped CSV file."""
    out_dir = os.path.join(os.getcwd(), "recordings")
    os.makedirs(out_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"recording_{timestamp}.csv"
    path = os.path.join(out_dir, filename)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["time (s)", "x (kg)", "y (kg)"])
        for row in record_buffer:
            writer.writerow([f"{row[0]:.3f}", f"{row[1]:.3f}", f"{row[2]:.3f}"])
    log.info("Recording saved to %s", path)
