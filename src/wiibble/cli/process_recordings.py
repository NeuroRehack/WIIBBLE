"""Offline posturographic analysis for WIIBBLE recordings."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import typer

from wiibble.analysis.analysis import analyse_recording
from wiibble.analysis.recording_meta import (
    MIN_ANALYSIS_DURATION_S,
    json_path_for,
    read_recording_duration_s,
)
from wiibble.cli.recordings_dir import collect_recording_csvs, get_recordings_dir
from wiibble.utils.logging_config import configure_logging

log = logging.getLogger(__name__)

app = typer.Typer(
    name="wiibble-process-recordings",
    help="Offline posturographic analysis for WIIBBLE recordings.",
    no_args_is_help=False,
    add_completion=False,
    rich_markup_mode=None,
)

_MIN_ANALYSIS_DURATION_S = MIN_ANALYSIS_DURATION_S


def _recordings_dir() -> Path:
    """Return the configured recordings directory from WIIBBLE settings."""
    return get_recordings_dir()


def _json_path_for(csv_path: Path) -> Path:
    """Return the JSON sidecar path that corresponds to *csv_path*."""
    return json_path_for(csv_path)


def _read_duration(csv_path: Path) -> float:
    """Return recording duration in seconds without loading the whole file."""
    return read_recording_duration_s(csv_path)


def _process_file(
    csv_path: Path,
    total_weight_kg: float | None,
    overwrite: bool,
    with_report: bool = True,
) -> bool:
    """Analyse *csv_path* and write JSON (and optional HTML report).

    Returns:
        True on success, False if skipped or failed.
    """
    json_path = _json_path_for(csv_path)

    if not overwrite and json_path.exists():
        typer.echo(f"  [skip] {csv_path.name} - JSON sidecar already exists", err=True)
        return False

    duration = _read_duration(csv_path)
    if duration < _MIN_ANALYSIS_DURATION_S:
        typer.echo(
            f"  [skip] {csv_path.name} - duration {duration:.1f} s < "
            f"{_MIN_ANALYSIS_DURATION_S:.0f} s minimum",
            err=True,
        )
        return False

    log.info("  [run]  %s (%.1f s) - starting analysis", csv_path.name, duration)
    try:
        t0 = time.time()
        features = analyse_recording(str(csv_path), total_weight_kg=total_weight_kg)
        json_path.write_text(
            json.dumps(features, indent=2, default=str), encoding="utf-8"
        )
        log.info(
            "    JSON written: %s (total %.2f s)", json_path.name, time.time() - t0
        )

        if with_report:
            try:
                from wiibble.cli.report import generate_report

                out_html = generate_report(str(csv_path), features_path=str(json_path))
                log.info("    HTML report written: %s", Path(out_html).name)
            except Exception:
                log.exception("Report generation failed for %s", csv_path)
        return True
    except Exception:
        log.exception("Analysis failed for %s", csv_path)
        return False


def _collect_all_csvs() -> list[Path]:
    """Return sorted recording CSV paths in the configured recordings directory."""
    return collect_recording_csvs()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    paths: list[Path] | None = typer.Argument(
        None,
        help="CSV recording file(s) to analyse",
        exists=True,
        dir_okay=False,
        readable=True,
    ),
    process_new: bool = typer.Option(
        False,
        "--new",
        help=(
            "Process unanalysed CSVs in the configured recordings directory "
            "(skip existing JSON sidecars)"
        ),
    ),
    reprocess_all: bool = typer.Option(
        False,
        "--all",
        help=(
            "Reprocess all CSVs in the configured recordings directory, "
            "overwriting JSON sidecars"
        ),
    ),
    weight: float | None = typer.Option(
        None,
        "--weight",
        metavar="KG",
        help="Override participant weight in kg (read from CSV header when omitted)",
    ),
    no_report: bool = typer.Option(
        False,
        "--no-report",
        help="Skip automatic HTML report generation after JSON analysis",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable DEBUG logging"),
) -> None:
    """Batch-analyse WIIBBLE recording CSV files."""
    configure_logging(
        level=logging.DEBUG if verbose else logging.INFO,
        log_to_file=False,
        stream=True,
    )

    if not paths and not process_new and not reprocess_all:
        typer.echo(ctx.get_help())
        raise typer.Exit(code=0)

    start_all = time.time()

    if paths:
        csv_files = paths
        overwrite = True
    else:
        recordings_dir = _recordings_dir()
        csv_files = _collect_all_csvs()
        if not csv_files:
            typer.echo(f"No recording CSVs found in '{recordings_dir}/'.")
            raise typer.Exit(code=0)
        overwrite = reprocess_all

    with_report = not no_report
    log.info("Processing %d file(s)...", len(csv_files))
    succeeded = sum(
        _process_file(
            p, total_weight_kg=weight, overwrite=overwrite, with_report=with_report
        )
        for p in csv_files
    )
    elapsed = time.time() - start_all
    typer.echo(
        f"Done - {succeeded}/{len(csv_files)} file(s) analysed "
        f"in {elapsed:.1f} seconds.",
        err=True,
    )


if __name__ == "__main__":
    app()
