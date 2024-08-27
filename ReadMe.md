# WIIBBLE - Wii Balance Board Live Environment

<div align="center">
  <img src="./images/logo.png" alt="WIIBBLE Logo" width="400">
</div>

### Overview
This project integrates the Wii Balance Board with custom software to measure weight and balance data. It aims to provide a live visualization of weight distribution and balance.


## Features

- Real-time data visualization of weight distribution
- Sensitivity calibration with a visual guide
- Tare functionality for more accurate measurements
- Easy setup for connecting to the Wii Balance Board via Bluetooth

## Prerequisites

- Wii Balance Board
- Windows 10/11
- Bluetooth-enabled computer
### Requirements for running from source and/or compiling
- Python 3.8+
- .NET 8.0
- .NET Framework 4.8

## Installation

1. **Clone the repository, navigate to the directory, and install the required packages:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Build the C# library:**
   
      Navigate to the `WiiBalanceBoardLibrary` directory and build the C# library using the following commands:
   
      ```bash
      cd WiiBalanceBoardLibrary
      dotnet build
      ```
### Compiling to an executable
To compile the python script you can run the `compiler.bat` file, this will create a folder called `outputBuild` with the executable inside.

## Usage

1. **Connect the Wii Balance Board:**

   Ensure that the Wii Balance Board is paired with your computer via Bluetooth. The blue LED should be blinking.

2. **Run the application:**

   Start the Python application by running the `main.py` script:

   ```bash
   python main.py
   ```

3. **Application Flow:**

   - The application will attempt to connect to the Wii Balance Board.
   - After connecting, follow the on-screen instructions for sensitivity calibration and tare functions.
   - Once calibrated, the live environment will display real-time weight distribution.

4. **Tare and Calibration:**

   The application will guide you through the tare and calibration process to ensure accurate weight measurement. Follow the on-screen instructions to step on and off the board as needed.

## Troubleshooting

- **Library Issues:** If the application fails to run due to library issues, try installing the required packages one at a time.

- **Connection Issues:** If the application fails to connect to the Wii Balance Board, ensure that:
  - Bluetooth is enabled on your computer.
  - The board is correctly paired and the LED is blinking blue.
  - The battery level is sufficient.
  
- **DLL Loading Issues:** Ensure that the `WiiBalanceBoardLibrary.dll` file is built and located in the correct path as specified in `board_connection.py`.
