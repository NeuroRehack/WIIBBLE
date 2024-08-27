# WIIBBLE - Wii Balance Board Live Environment

<div align="center">
  <img src="./images/logo.png" alt="WIIBBLE Logo" width="400">
</div>

### Overview
This project integrates the Wii Balance Board with custom software to measure weight and balance data. It aims to provide a live visualization of weight distribution and balance.

The project consists of two main components: a C# program (`Program.cs`) to enable connection to the Wii Balance Board and a Python script (`scale.py`) to visualize the balance data using Pygame.

### Components
1. **C# Application (`Program.cs`)**
   - Connects to the Wii Balance Board using the WiimoteLib.

2. **Python Script (`scale.py`)**
   - Uses the HID library to connect to the Wii Balance Board and read data.
   - Utilizes Pygame to display visual feedback based on weight distribution and balance.

### Installation and Setup

1. **Prerequisites:**
   - .NET SDK for building the C# application.
   - Python 3.x and necessary libraries (`hid`, `pygame`, `numpy`, `pygame_gui`).

2. **Building the C# Application:**
   - Navigate to the `WiiBalanceBoardConnection` directory.
   - Use the command `dotnet build` to compile the project.
   - The compiled executable will be found in the `bin` directory.

3. **Running the Python Script:**
   - Ensure all required Python libraries are installed. You can install them using:
     ```
     pip install -r requirements.txt
     ```
   - Run the script with:
     ```
     python scale.py
     ```

### Usage

1. **Connecting the Wii Balance Board:**
   - Ensure the board is paired with your computer via Bluetooth.
   - Execute the Python script to visualize the data.

2. **Visual Feedback:**
   - The Pygame window will display a live view of the weight distribution and balance. 
   - Follow on-screen instructions for calibration and data visualization.

### Troubleshooting

- If the Wii Balance Board is not detected, ensure Bluetooth is enabled and the board is properly paired.
- Check the console output for error messages and follow suggested fixes.
