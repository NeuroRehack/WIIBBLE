# WIIBBLE Data Processing Pipeline

This document outlines the data processing pipeline for the WIIBBLE application, from raw sensor acquisition to CSV recording output.

---

## 1. Data Acquisition
- **Source:** Wii Balance Board (or mock device)
- **Function:** `read_data(device)`
- **Description:** Reads a 32-byte HID report from the device each frame.
- **Output:** Raw byte array (list of 32 integers)

---

## 2. Parsing & Tare Correction
- **Function:** `parse_data(data, data_struct)`
- **Description:**
  - Extracts sensor values for each corner from the raw byte array.
  - Applies tare (baseline) correction using values in `data_struct`.
  - Formula: `(data[i] + data[i+1] / 255 - tare) * SCALE_FACTOR`
- **Output:** Dictionary of corner weights in kg: `{top_left, top_right, bottom_left, bottom_right}`

---

## 3. Filtering (Noise Reduction)
- **Function:** `apply_filter(corners, filter_buffer, filter_window)`
- **Description:**
  - Implements a moving average filter over the last N frames (`filter_window`).
  - Reduces sensor noise before further calculations.
- **Output:** Smoothed corner weights in kg (same structure as above)

---

## 4. Force Deviation Calculation
- **Function:** `calculate_force_deviation_kg(top_left, top_right, bottom_left, bottom_right)`
- **Description:**
  - Computes net left-right (x) and front-back (y) force deviations in kg.
  - x = (top_right + bottom_right) - (top_left + bottom_left)
  - y = (top_left + top_right) - (bottom_left + bottom_right)
- **Output:** Tuple `(x, y)` in kg

---

## 5. Coordinate Calculation (for UI)
- **Function:** `calculate_coordinates(...)`
- **Description:**
  - Converts filtered corner weights to screen coordinates.
  - Normalizes by total weight, scales to screen size and zoom.
- **Output:** Tuple `(x, y)` in screen pixels

---

## 6. Buffering for Recording
- **Location:** Main loop in `app.py`
- **Description:**
  - Each frame during recording, appends `(timestamp, x, y)` to `app_state.record_buffer`.
  - Timestamp is relative to recording start.
- **Output:** List of tuples for CSV export

---

## 7. CSV Output
- **Function:** `_save_recording_csv(record_buffer)`
- **Description:**
  - Writes the buffer to a CSV file in the `recordings/` directory after recording ends.
  - Each row: `time (s), x (kg), y (kg)`

---

## 8. Sampling Rate
- **Target:** 100 Hz maximum (capped in main loop, but not strictly enforced)
- **Actual:** Depends on system performance and frame rate

---

## Pipeline Diagram

```
Raw HID Data (32 bytes)
   ↓
parse_data + tare
   ↓
Moving Average Filter (apply_filter)
   ↓
Force Deviation (calculate_force_deviation_kg)
   ↓
Buffer (timestamp, x, y)
   ↓
CSV Output (_save_recording_csv)
```

---

## Notes
- Filtering is applied before any coordinate or force calculations.
- All processing is done in real time, frame by frame.
- The pipeline is identical for both real and mock data sources.
