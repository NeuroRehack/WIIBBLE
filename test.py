import clr
import os
import sys
import time
from System import AppDomain, Activator

# Define the path to the DLL
dll_path = r'WiiBalanceBoardConnection\WiiBalanceBoardLibrary\bin\Debug\net48\WiiBalanceBoardLibrary.dll'
assert os.path.exists(dll_path), "DLL file not found at the specified path."

# Add reference to the DLL
clr.AddReference(dll_path)

# Get the assembly containing the classes we need
try:
    assembly = next(a for a in AppDomain.CurrentDomain.GetAssemblies() if "WiiBalanceBoardLibrary" in str(a))
    BalanceBoardManager = assembly.GetType("WiiBalanceBoardLibrary.BalanceBoardManager")
    BalanceBoardDataEventArgs = assembly.GetType("WiiBalanceBoardLibrary.BalanceBoardDataEventArgs")
    print("Successfully accessed BalanceBoardManager and BalanceBoardDataEventArgs classes.")
except Exception as e:
    print(f"Error accessing classes: {e}")
    sys.exit(1)

# Event handler function for data reception
def on_balance_board_data_received(sender, event_args):
    print(f"Weight: {event_args.Weight:.2f} kg")
    print(f"Top Right: {event_args.TopRight:.2f} kg")
    print(f"Top Left: {event_args.TopLeft:.2f} kg")
    print(f"Bottom Right: {event_args.BottomRight:.2f} kg")
    print(f"Bottom Left: {event_args.BottomLeft:.2f} kg")
    
    # Assuming event_args or a property provides access to the battery level
    try:
        # Retrieve battery level from the manager instance
        battery_level = manager_instance.BatteryLevel
        print(f"Battery Level: {battery_level:.2f}%")
    except AttributeError:
        print("Battery level information is not available.")

# Create an instance of BalanceBoardManager
try:
    manager_instance = Activator.CreateInstance(BalanceBoardManager)
    print("Instance of BalanceBoardManager created.")

    # Set up the event handler for data reception
    manager_instance.BalanceBoardDataReceived += on_balance_board_data_received

    # Connect to the balance board
    try:
        manager_instance.Connect()
        print("Connected to the balance board. Waiting for data...")
    except Exception as e:
        print(f"Error connecting to the balance board: {e}")
        sys.exit(1)

    # Wait for data to be received
    while not manager_instance.IsDataRead:
        time.sleep(0.1)

    print("Data received. Exiting...")
    sys.exit(0)

finally:
    # Ensure proper disconnection
    try:
        manager_instance.Disconnect()
        print("Disconnected from the balance board.")
    except Exception as e:
        print(f"Error disconnecting from the balance board: {e}")
