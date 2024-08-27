import clr
import os
import sys
import time
from System import AppDomain, Activator

# Constants
DLL_RELATIVE_PATH = r'.\libs\WiiBalanceBoardLibrary.dll'
SLEEP_INTERVAL = 0.1

# Helper Functions
def get_dll_path():
    """Return the absolute path to the DLL file and verify its existence."""
    dll_path = os.path.abspath(DLL_RELATIVE_PATH)
    if not os.path.exists(dll_path):
        raise FileNotFoundError(f"DLL file not found at {dll_path}")
    print(f"Full path to DLL: {dll_path}")
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
        print("Successfully accessed BalanceBoardManager and BalanceBoardDataEventArgs classes.")
        return BalanceBoardManager, BalanceBoardDataEventArgs
    except Exception as e:
        raise Exception(f"Error accessing classes: {e}")

def create_balance_board_manager(BalanceBoardManager):
    """Create an instance of the BalanceBoardManager class."""
    try:
        manager_instance = Activator.CreateInstance(BalanceBoardManager)
        print("Instance of BalanceBoardManager created.")
        return manager_instance
    except Exception as e:
        raise Exception(f"Error creating instance of BalanceBoardManager: {e}")

def connect_balance_board(manager_instance):
    """Attempt to connect to the Wii Balance Board."""
    try:
        manager_instance.Connect()
        print("Connected to the balance board. Waiting for data...")
    except Exception as e:
        raise Exception(f"Error connecting to the balance board: {e}")

def disconnect_balance_board(manager_instance):
    """Safely disconnect from the Wii Balance Board."""
    try:
        manager_instance.Disconnect()
        print("Disconnected from the balance board.")
    except Exception as e:
        print(f"Error disconnecting from the balance board: {e}")

# Event Handlers
def on_balance_board_data_received(sender, event_args):
    """Handle the balance board data received event."""
    print(f"Weight: {event_args.Weight:.2f} kg")
    print(f"Top Right: {event_args.TopRight:.2f} kg")
    print(f"Top Left: {event_args.TopLeft:.2f} kg")
    print(f"Bottom Right: {event_args.BottomRight:.2f} kg")
    print(f"Bottom Left: {event_args.BottomLeft:.2f} kg")
    
    # Attempt to retrieve battery level
    try:
        battery_level = manager_instance.BatteryLevel
        print(f"Battery Level: {battery_level:.2f}%")
    except AttributeError:
        print("Battery level information is not available.")

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

        print("Data received. Exiting...")

    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

    finally:
        disconnect_balance_board(manager_instance)
