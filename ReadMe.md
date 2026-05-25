<!-- add shields -->

# WIIBBLE - Wii Balance Board Live Environment

<div align="center">
  <img src="./images/logo.png" alt="WIIBBLE Logo" width="400">
</div>

---
WIIBBLE, a tool designed to repurpose the Wii Balance Board for clinical use in rehabilitation settings. WIIBBLE allows clinicians to integrate the balance board into their practice, providing an additional resource for patient rehabilitation.

This project integrates the Wii Balance Board with custom software to measure weight and balance data. It aims to provide a live visualization of weight distribution and balance.

- [WIIBBLE - Wii Balance Board Live Environment](#wiibble---wii-balance-board-live-environment)
  - [💡 Features  ](#-features--)
  - [📝 Prerequisites ](#-prerequisites-)
  - [🧑‍💻 Development Without Hardware](#-development-without-hardware)
    - [Mock Mode](#mock-mode)
    - [⚙️ Requirements for running from source and/or compiling](#️-requirements-for-running-from-source-andor-compiling)
  - [🚀 Getting Started ](#-getting-started-)
  - [🔧 Board pairing ](#-board-pairing-)
    - [😀 Case 1: Bluetooth mac address does not contain "00" ](#-case-1-bluetooth-mac-address-does-not-contain-00-)
    - [😭 Case 2: Bluetooth mac address contains "00" ](#-case-2-bluetooth-mac-address-contains-00-)
  - [🔨 Installation from Source ](#-installation-from-source-)
    - [💻 Compiling to an executable ](#-compiling-to-an-executable-)
  - [📄 Usage ](#-usage-)
    - [Running in Mock Mode](#running-in-mock-mode)
  - [🚑 Troubleshooting ](#-troubleshooting-)
  - [🙏 Acknowledgements: ](#-acknowledgements-)



## 💡 Features  <a name="features"></a>
- Simple real-time data visualization of weight distribution
- Sensitivity calibration
- Tare functionality for more accurate measurements
- Easy setup for connecting to the Wii Balance Board via Bluetooth *(after pairing: see [Board Pairing in the User Manual](Docs/USER_MANUAL.md#board-pairing))*
- **Recording feature:** Record weight and balance data for a set duration or stop manually, with export to CSV for further analysis


## 📝 Prerequisites <a name="prerequisites"></a>
For prerequisites, supported platforms, and required tool versions, see [DEV.md](Docs/DEV.md#prerequisites).

## 🧑‍💻 Development Without Hardware

WIIBBLE can be developed and tested **without a physical Wii Balance Board** using the built-in mock mode. See scenarios and full details/manual in [USER_MANUAL.md](Docs/USER_MANUAL.md#command-line-options).


## 🚀 Getting Started <a name="getting-started"></a>
1. **Download the latest release** from [here](https://github.com/NeuroRehack/WIIBBLE/releases)
     - or clone the repository and follow the instructions at [Developer Setup & Workflow Guide](Docs/DEV.md).
2. **Pair the Wii Balance Board with your computer** (see [Board Pairing in the User Manual](Docs/USER_MANUAL.md#board-pairing)).
3. **Head to the [Usage section in the User Manual](Docs/USER_MANUAL.md#data-recording) for instructions on running and recording with the application.**



## 🔧 Board pairing <a name="board-pairing"></a>
For full step-by-step instructions and troubleshooting for pairing the Wii Balance Board over Bluetooth, see the [Board Pairing section in the User Manual](Docs/USER_MANUAL.md#board-pairing).

## 🔨 Installation from Source <a name="installation-from-source"></a>
For full developer setup, dependency installation, and build/test/packaging workflow, see the [Developer Setup & Workflow Guide](Docs/DEV.md).

Quickstart:
1. Clone the repository and install dependencies:
   ```powershell
   git clone https://github.com/NeuroRehack/WIIBBLE.git
   cd WIIBBLE
   uv sync
   ```
2. For building, packaging, and in-depth instructions, follow [DEV.md](Docs/DEV.md).

## 📄 Usage <a name="usage"></a>

### Running in Mock Mode

- To run the app without hardware:
  ```bash
  python main.py --mock --mock-scenario sway
  ```
  Replace `[scenario]` with one of: `still`, `sway`, `lean_left`, `lean_right`, `hands`.

1. **Connect the Wii Balance Board:**

   Ensure that the Wii Balance Board is paired (see [Board Pairing](#board-pairing)) with your computer via Bluetooth.
2. **Press the button on the Wii Balance Board:**

   The blue LED should be blinking.

3. **Run the application:**

   If running from source: 
   
   -  Start the Python application by running the `main.py` script

   If running the executable:

   - Run the executable from the `outputBuild` folder or the location where you downloaded the executable to.


---

3. **Application Flow:**

  - The application will attempt to connect to the Wii Balance Board.
  - After connecting, follow the on-screen instructions for sensitivity calibration and tare functions.
  - Once calibrated, the live environment will display real-time weight distribution.

## 🚑 Troubleshooting <a name="troubleshooting"></a>
For troubleshooting common issues (connection, libraries, board not found, DLLs), see the [Troubleshooting section in the User Manual](Docs/USER_MANUAL.md#troubleshooting).

## 🙏 Acknowledgements: <a name="acknowledgements"></a>
- This project was developed as part of the **EPIC-Tech study** in collaboration with **The University of Queensland**, **Griffith University**, and **Metro South Princess Alexandra Hospital**.
- Thanks to the physiotherapists at the [Princess Alexandra Hospital - Geriatric And Rehabilitation Unit](https://www.healthdirect.gov.au/australian-health-services/healthcare-service/woolloongabba-4102-qld/princess-alexandra-hospital-geriatric-and-rehabilitation-unit/geriatric-medicine/efcf3c01-fc12-46fc-2912-691b09238616) for their feedback and guidance.
- [WiiBalanceWalker](https://github.com/lshachar/WiiBalanceWalker) for the Wii Balance Board connection library.
- [code_descriptors_postural_control](https://github.com/Jythen/code_descriptors_postural_control) by **Jythen** — vendored at `code_descriptors_postural_control/` and used for posturographic feature extraction ([details](code_descriptors_postural_control/VENDOR.md)).

