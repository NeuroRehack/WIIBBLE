"""Generate an end-of-session posturographic HTML report for one recording."""

from __future__ import annotations

import logging
from pathlib import Path

import typer

from wiibble.session_report.runner import run_session_report
from wiibble.utils.logging_config import configure_logging

log = logging.getLogger(__name__)


def main(
    csv_path: Path = typer.Argument(
        ...,
        help="Path to a WIIBBLE recording CSV",
        exists=True,
        dir_okay=False,
        readable=True,
    ),
    open_browser: bool = typer.Option(
        False,
        "--open/--no-open",
        help="Open the HTML report in the default browser when finished",
    ),
    out: Path | None = typer.Option(
        None,
        "--out",
        help="Destination HTML path (default: report_<timestamp>.html next to CSV)",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable DEBUG logging"),
) -> None:
    """Run analysis (when duration >= 20 s) and write an HTML report."""
    configure_logging(
        level=logging.DEBUG if verbose else logging.INFO,
        log_to_file=False,
        stream=True,
    )
    try:
        report_path = run_session_report(
            csv_path,
            open_browser=open_browser,
            out_path=out,
        )
        typer.echo(str(report_path))
    except FileNotFoundError:
        log.exception("Recording not found")
        raise typer.Exit(code=1) from None
    except Exception:
        log.exception("Session report failed for %s", csv_path)
        raise typer.Exit(code=2) from None


def cli() -> None:
    """Console script entry point for wiibble-session-report."""
    typer.run(main)


if __name__ == "__main__":
    cli()
