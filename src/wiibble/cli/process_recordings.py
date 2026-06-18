"""Offline posturographic analysis for WIIBBLE recordings.

Usage
-----
Process all unanalysed CSVs in recordings/ (skip existing JSON sidecars)::

    python process_recordings.py --new

Process specific file(s)::

    python process_recordings.py recordings/recording_20260325_211625.csv

Reprocess everything, overwriting existing JSON sidecars::

    python process_recordings.py --all

Dependencies
------------
Requires the *analysis* optional extras::

    uv sync --extra analysis

"""

import argparse
import json
import logging
import os
import sys
import time

from wiibble.analysis.analysis import analyse_recording

start_all = time.time()
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger(__name__)
log.info("Starting WIIBBLE posturographic batch analysis script…")
log.info("Importing analysis library and all dependencies…")

log.info("Imports complete.")


# Recordings shorter than this will be skipped — too few samples for reliable
# posturographic estimates (SWARII resamples to 25 Hz; 30 s is the standard).
_MIN_ANALYSIS_DURATION_S = 20.0

_RECORDINGS_DIR = "recordings"


def _json_path_for(csv_path: str) -> str:
    """Return the JSON sidecar path that corresponds to *csv_path*."""
    stem = os.path.splitext(os.path.basename(csv_path))[0]
    if stem.startswith("recording_"):
        return stem.replace("recording_", "features_", 1) + ".json"
    return f"features_{stem}.json"


def _read_duration(csv_path: str) -> float:
    """Return recording duration in seconds without loading the whole file."""
    first_ts: float | None = None
    last_ts: float | None = None
    with open(csv_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(",")
            try:
                ts = float(parts[0])
            except ValueError:
                continue  # header row
            if first_ts is None:
                first_ts = ts
            last_ts = ts
    if first_ts is None or last_ts is None:
        return 0.0
    return last_ts - first_ts


def _process_file(
    csv_path: str, total_weight_kg: float | None, overwrite: bool, with_report: bool = True
) -> bool:
    """Analyse *csv_path*, write JSON sidecar, then HTML report if requested.

    Returns True on success, False if skipped or failed.
    *total_weight_kg* is passed through to :func:`analyse_recording`; when
    ``None`` the function reads the value from the CSV header comment.
    """
    json_path = _json_path_for(csv_path)

    if not overwrite and os.path.exists(json_path):
        print(f"  [skip] {os.path.basename(csv_path)} — JSON sidecar already exists")
        return False

    duration = _read_duration(csv_path)
    if duration < _MIN_ANALYSIS_DURATION_S:
        print(
            f"  [skip] {os.path.basename(csv_path)} — duration {duration:.1f} s < "
            f"{_MIN_ANALYSIS_DURATION_S:.0f} s minimum"
        )
        return False

    log.info(f"  [run]  {os.path.basename(csv_path)} ({duration:.1f} s) — starting analysis")
    log.info("Beginning analysis of file: %s", csv_path)
    try:
        t0 = time.time()
        log.info(
            "    Running analyse_recording (this may take a moment for large files or first run)…"
        )
        features = analyse_recording(csv_path, total_weight_kg=total_weight_kg)
        t1 = time.time()
        log.info(f"    analyse_recording done in {t1 - t0:.2f} s. Writing JSON…")
        log.info("analyse_recording complete in %.2f s for %s", (t1 - t0), csv_path)
        with open(json_path, "w", encoding="utf-8") as fh:
            json.dump(features, fh, indent=2, default=str)
        t2 = time.time()
        log.info(f"    JSON written: {os.path.basename(json_path)} (total {t2 - t0:.2f} s)")
        # --- HTML report generation ---
        if with_report:
            try:
                log.info("    Generating HTML report…")
                from wiibble.cli.report import generate_report

                out_html = generate_report(csv_path, features_path=json_path)
                log.info(f"    HTML report written: {os.path.basename(out_html)}")
            except Exception as exc:
                log.error(f"    Report generation FAILED: {exc}")
                log.exception("Report generation failed for %s", csv_path)
        return True
    except Exception as exc:
        log.error(f"FAILED ({exc})")
        log.exception("Analysis failed for %s", csv_path)
        return False


def _collect_all_csvs() -> list[str]:
    """Return sorted list of recording CSVs in the recordings directory."""
    if not os.path.isdir(_RECORDINGS_DIR):
        return []
    paths = [
        os.path.join(_RECORDINGS_DIR, f)
        for f in sorted(os.listdir(_RECORDINGS_DIR))
        if f.endswith(".csv")
    ]
    return paths


def main() -> int:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

    parser = argparse.ArgumentParser(
        description="Offline posturographic analysis for WIIBBLE recordings.",
        epilog=(
            "Examples:\n"
            "  python process_recordings.py --new\n"
            "  python process_recordings.py recordings/recording_20260325_211625.csv\n"
            "  python process_recordings.py --all"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "paths",
        nargs="*",
        metavar="FILE",
        help="CSV recording file(s) to analyse.",
    )
    parser.add_argument(
        "--new",
        action="store_true",
        dest="process_new",
        help=f"Process all unanalysed CSVs in '{_RECORDINGS_DIR}/' (skip existing JSON sidecars).",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        dest="reprocess_all",
        help=f"Reprocess all CSVs in '{_RECORDINGS_DIR}/', overwriting existing JSON sidecars.",
    )
    parser.add_argument(
        "--weight",
        type=float,
        default=None,
        metavar="KG",
        help=(
            "Override participant weight in kg (read from CSV header when omitted). "
            "Only useful when processing a single file whose header is missing this value."
        ),
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        dest="no_report",
        help="Disable automatic report (HTML) generation after JSON analysis. [default: reports are generated]",
    )

    args = parser.parse_args()

    # No arguments — show help
    if not args.paths and not args.process_new and not args.reprocess_all:
        parser.print_help()
        return 0

    if args.paths:
        csv_files = args.paths
        for p in csv_files:
            if not os.path.isfile(p):
                print(f"ERROR: file not found: {p}", file=sys.stderr)
                return 1
        overwrite = True
    else:
        csv_files = _collect_all_csvs()
        if not csv_files:
            print(f"No recording CSVs found in '{_RECORDINGS_DIR}/'.")
            return 0
        overwrite = args.reprocess_all

    # Pass the flag to processing step (report generation is ON by default)
    with_report = not args.no_report

    log.info(f"Processing {len(csv_files)} file(s)…")
    succeeded = sum(
        _process_file(p, total_weight_kg=args.weight, overwrite=overwrite, with_report=with_report)
        for p in csv_files
    )
    elapsed = time.time() - start_all
    log.info(f"Done — {succeeded}/{len(csv_files)} file(s) analysed in {elapsed:.1f} seconds.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
