"""WIIBBLE GUI entry point (`python -m wiibble` / `wiibble` CLI)."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import dearpygui.dearpygui as dpg
import typer

from wiibble.session import run
from wiibble.ui.theme import apply_global_theme, load_fonts
from wiibble.utils.display import get_screen_size
from wiibble.utils.logging_config import (
    configure_logging,
    install_uncaught_exception_hook,
)
from wiibble.utils.state import AppState, Settings

log = logging.getLogger(__name__)

MOCK_SCENARIOS = [
    "sway",
    "still",
    "lean_left",
    "lean_right",
    "hands",
    "step_on_off",
    "calibration",
]

app = typer.Typer(
    name="wiibble",
    help="Wii Balance Board Live Environment.",
    no_args_is_help=False,
    add_completion=False,
)


@dataclass
class LaunchOptions:
    """Runtime options parsed from the WIIBBLE CLI."""

    mock: bool = False
    mock_scenario: str = "sway"


@app.callback(invoke_without_command=True)
def main(
    mock: bool = typer.Option(False, "--mock", help="Run with simulated sensor data"),
    mock_scenario: str = typer.Option(
        "sway",
        "--mock-scenario",
        help="Mock scenario name",
        case_sensitive=False,
    ),
) -> None:
    """Launch the WIIBBLE desktop application."""
    configure_logging(level=logging.INFO, log_to_file=True, stream=True)
    install_uncaught_exception_hook(log)

    if mock_scenario.lower() not in MOCK_SCENARIOS:
        typer.echo(
            "Invalid mock scenario "
            f"{mock_scenario!r}. Choose from: {', '.join(MOCK_SCENARIOS)}",
            err=True,
        )
        raise typer.Exit(code=1)

    options = LaunchOptions(mock=mock, mock_scenario=mock_scenario.lower())
    log.info(
        "Starting WIIBBLE (mock=%s, scenario=%s)", options.mock, options.mock_scenario
    )

    try:
        dpg.create_context()
        settings = Settings.load()
        screen_w, screen_h = get_screen_size()

        app_state = AppState(
            screen_width=screen_w,
            screen_height=screen_h * 0.9,
            historical_coords=[(0, 0)] * settings.trail_length,
        )

        load_fonts()
        dpg.setup_dearpygui()
        apply_global_theme()

        dpg.create_viewport(
            title="WIIBBLE - Wii Balance Board Live Environment",
            width=screen_w,
            height=screen_h,
            x_pos=0,
            y_pos=0,
            small_icon="images/logoPerson.ico",
            large_icon="images/logoPerson.ico",
        )
        dpg.show_viewport()
        dpg.maximize_viewport()

        run(app_state, settings, options)
    except Exception:
        log.exception("Fatal exception in main")
        raise typer.Exit(code=1) from None
    finally:
        dpg.destroy_context()


if __name__ == "__main__":
    app()
