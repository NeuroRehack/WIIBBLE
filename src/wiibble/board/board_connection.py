"""C# DLL bridge for the Wii Balance Board Bluetooth handshake."""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

import clr
from System import Activator, AppDomain

from wiibble.board.exceptions import DeviceNotFoundError, DeviceProtocolError

log = logging.getLogger(__name__)

DLL_RELATIVE_PATH = (
    Path("WiiBalanceBoardLibrary") / "bin" / "Debug" / "net48" / "WiiBalanceBoardLibrary.dll"
)
SLEEP_INTERVAL = 0.1


def get_dll_path() -> Path:
    """Return the absolute path to the DLL file and verify its existence."""
    dll_path = DLL_RELATIVE_PATH.resolve()
    if not dll_path.is_file():
        raise DeviceNotFoundError(f"DLL file not found at {dll_path}")
    log.debug("Full path to DLL: %s", dll_path)
    return dll_path


def load_dll(dll_path: Path):
    """Load the DLL and add it to the Python environment."""
    clr.AddReference(str(dll_path))
    return next(
        a for a in AppDomain.CurrentDomain.GetAssemblies() if "WiiBalanceBoardLibrary" in str(a)
    )


def get_class_types(assembly):
    """Retrieve the necessary class types from the loaded assembly."""
    try:
        balance_board_manager = assembly.GetType("WiiBalanceBoardLibrary.BalanceBoardManager")
        balance_board_data_event_args = assembly.GetType(
            "WiiBalanceBoardLibrary.BalanceBoardDataEventArgs"
        )
        log.debug(
            "Successfully accessed BalanceBoardManager and BalanceBoardDataEventArgs classes."
        )
        return balance_board_manager, balance_board_data_event_args
    except Exception as exc:
        raise DeviceProtocolError(f"Error accessing DLL classes: {exc}") from exc


def create_balance_board_manager(balance_board_manager):
    """Create an instance of the BalanceBoardManager class."""
    try:
        manager_instance = Activator.CreateInstance(balance_board_manager)
        log.debug("Instance of BalanceBoardManager created.")
        return manager_instance
    except Exception as exc:
        raise DeviceProtocolError(f"Error creating instance of BalanceBoardManager: {exc}") from exc


def connect_balance_board(manager_instance) -> None:
    """Attempt to connect to the Wii Balance Board."""
    try:
        manager_instance.Connect()
        log.info("Connected to the balance board. Waiting for data...")
    except Exception as exc:
        raise DeviceProtocolError(f"Error connecting to the balance board: {exc}") from exc


def disconnect_balance_board(manager_instance) -> None:
    """Safely disconnect from the Wii Balance Board."""
    try:
        manager_instance.Disconnect()
        log.info("Disconnected from the balance board.")
    except Exception as exc:
        log.error("Error disconnecting from the balance board: %s", exc)


def on_balance_board_data_received(sender, event_args) -> None:
    """Handle the balance board data received event."""
    log.debug(
        "Board data: total=%.2f kg  TR=%.2f  TL=%.2f  BR=%.2f  BL=%.2f",
        event_args.Weight,
        event_args.TopRight,
        event_args.TopLeft,
        event_args.BottomRight,
        event_args.BottomLeft,
    )


def try_connection(dll_path: str | Path | None = None, mock_mode: bool = False) -> int:
    """Try to connect to the Wii Balance Board.

    Returns:
        0 if successful, 1 if failed. In mock mode, returns 0 immediately.
    """
    if mock_mode:
        log.debug("Skipping DLL connection in mock mode.")
        return 0

    manager_instance = None
    try:
        resolved = get_dll_path() if dll_path is None else Path(dll_path).resolve()
        assembly = load_dll(resolved)
        balance_board_manager, _ = get_class_types(assembly)
        manager_instance = create_balance_board_manager(balance_board_manager)
        connect_balance_board(manager_instance)
        return 0
    except Exception:
        log.exception("An error occurred in try_connection")
        return 1
    finally:
        if manager_instance is not None:
            try:
                disconnect_balance_board(manager_instance)
            except Exception:
                pass


if __name__ == "__main__":
    try:
        dll = get_dll_path()
        assembly = load_dll(dll)
        balance_board_manager, balance_board_data_event_args = get_class_types(assembly)

        manager_instance = create_balance_board_manager(balance_board_manager)
        manager_instance.BalanceBoardDataReceived += on_balance_board_data_received

        connect_balance_board(manager_instance)

        while not manager_instance.IsDataRead:
            time.sleep(SLEEP_INTERVAL)

        log.info("Data received. Exiting...")

    except Exception:
        log.exception("An error occurred in main")
        sys.exit(1)

    finally:
        disconnect_balance_board(manager_instance)
