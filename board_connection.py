import clr
import logging
import os
import sys
import time
from System import AppDomain, Activator

log = logging.getLogger(__name__)


# Cross-platform DLL path
DLL_RELATIVE_PATH = os.path.join('WiiBalanceBoardLibrary', 'bin', 'Debug', 'net48', 'WiiBalanceBoardLibrary.dll')
SLEEP_INTERVAL = 0.1

# Helper Functions
def get_dll_path():
    """Return the absolute path to the DLL file and verify its existence."""
    dll_path = os.path.abspath(DLL_RELATIVE_PATH)
    if not os.path.exists(dll_path):
        raise FileNotFoundError(f"DLL file not found at {dll_path}")
    log.debug("Full path to DLL: %s", dll_path)
    return dll_path

def load_dll(dll_path):
    """Load the DLL and add it to the Python environment."""
    clr.AddReference(dll_path)
    return next(a for a in AppDomain.CurrentDomain.GetAssemblies() if "WiiBalanceBoardLibrary" in str(a))

def get_class_types(assembly):
    """Retrieve the necessary class types from the loaded assembly."""
    try:
        BalanceBoardManager = assembly.GetType("WiiBalanceBoardLibrary.BalanceBoardManager")
        BalanceBoardDataEventArgs = assembly.GetType("WiiBalanceBoardLibrary.BalanceBoardDataEventArgs")
        log.debug("Successfully accessed BalanceBoardManager and BalanceBoardDataEventArgs classes.")
        return BalanceBoardManager, BalanceBoardDataEventArgs
    except Exception as e:
        raise Exception(f"Error accessing classes: {e}")

def create_balance_board_manager(BalanceBoardManager):
    """Create an instance of the BalanceBoardManager class."""
    try:
        manager_instance = Activator.CreateInstance(BalanceBoardManager)
        log.debug("Instance of BalanceBoardManager created.")
        return manager_instance
    except Exception as e:
        raise Exception(f"Error creating instance of BalanceBoardManager: {e}")

def connect_balance_board(manager_instance):
    """Attempt to connect to the Wii Balance Board."""
    try:
        manager_instance.Connect()
        log.info("Connected to the balance board. Waiting for data...")
    except Exception as e:
        raise Exception(f"Error connecting to the balance board: {e}")

def disconnect_balance_board(manager_instance):
    """Safely disconnect from the Wii Balance Board."""
    try:
        manager_instance.Disconnect()
        log.info("Disconnected from the balance board.")
    except Exception as e:
        log.error("Error disconnecting from the balance board: %s", e)

# Event Handlers
def on_balance_board_data_received(sender, event_args):
    """Handle the balance board data received event."""
    log.debug("Weight: %.2f kg", event_args.Weight)
    log.debug("Top Right: %.2f kg", event_args.TopRight)
    log.debug("Top Left: %.2f kg", event_args.TopLeft)
    log.debug("Bottom Right: %.2f kg", event_args.BottomRight)
    log.debug("Bottom Left: %.2f kg", event_args.BottomLeft)

    # Attempt to retrieve battery level
    try:
        battery_level = manager_instance.BatteryLevel
        log.debug("Battery Level: %.2f%%", battery_level)
    except AttributeError:
        log.debug("Battery level information is not available.")

def try_connection(dll_path=None, mock_mode=False):
    """ Try to connect to the Wii Balance Board. Returns 0 if successful, 1 if failed. In mock mode, returns 0 immediately. """
    if mock_mode:
        log.debug("Skipping DLL connection in mock mode.")
        return 0
    try:
        dll_path = get_dll_path() if dll_path is None else dll_path
        assembly = load_dll(dll_path)
        BalanceBoardManager, BalanceBoardDataEventArgs = get_class_types(assembly)
        manager_instance = create_balance_board_manager(BalanceBoardManager)
        connect_balance_board(manager_instance)
        return 0
    except Exception as e:
        log.exception("An error occurred in try_connection")
        return 1
    finally:
        try:
            disconnect_balance_board(manager_instance)
        except Exception:
            pass

# Main Execution Flow
if __name__ == "__main__":
    try:
        dll_path = get_dll_path()
        assembly = load_dll(dll_path)
        BalanceBoardManager, BalanceBoardDataEventArgs = get_class_types(assembly)
        
        manager_instance = create_balance_board_manager(BalanceBoardManager)
        manager_instance.BalanceBoardDataReceived += on_balance_board_data_received

        connect_balance_board(manager_instance)

        # Wait for data reception
        while not manager_instance.IsDataRead:
            time.sleep(SLEEP_INTERVAL)

        log.info("Data received. Exiting...")

    except Exception as e:
        log.exception("An error occurred in main")
        sys.exit(1)

    finally:
        disconnect_balance_board(manager_instance)
