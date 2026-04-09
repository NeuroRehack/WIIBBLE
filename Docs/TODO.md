# WIIBBLE — TODO & Roadmap

- [WIIBBLE — TODO \& Roadmap](#wiibble--todo--roadmap)
  - [🟢Feature requests and improvements](#feature-requests-and-improvements)
  - [🔴 Bugs](#-bugs)
    - [UI](#ui)
    - [Functionality](#functionality)
    - [Installation](#installation)
  - [🟡 Code Quality](#-code-quality)
  - [🟢 Developer Experience](#-developer-experience)
    - [Add Logging Framework](#add-logging-framework)
    - [Add GitHub Actions CI Pipeline](#add-github-actions-ci-pipeline)
    - [Add Unit Tests](#add-unit-tests)
  - [🟢 Project Structure](#-project-structure)


---

##  🟢Feature requests and improvements
 - [x] Add a stop watch timer to the UI during recording sessions for better user feedback on elapsed time
 - [x] Modify zoom feature to allow offcenter zooming, not just zooming to the center of the screen. This would allow users to focus on specific areas of the workspace.
 - [x] Add slider to adjust the sensitivity, which is calculated during the calibration phase. This would allow users to fine-tune the cursor movement to their preference or needs.
 - [x] change stat bar coulour back to dinamic colour range based on amount of weight on the board
 - [ ] Add option to manually recalibrate the board. Currently, we use a constant SCALE_FACTOR to convert raw sensor values to weight, but this can vary between boards and over time. A manual calibration option would allow users to adjust the scale factor based on known weights for improved accuracy.
 - [x] migrate the blurry draw text to a custom font rendering system
 - [x] allow resizing of target spots

## 🔴 Bugs
### UI
- [ ] Remove the settings button from any screen except the main session screen. It currently appears during tare, calibration, connction and failed connection screens, which is confusing since it doesn't do anything in those contexts.
- [x] Interface issue: Settings button and the whole bar disappears by
changing the screen size (windowed mode and full-screen mode )
- [x] Interface issue: on smaller screen the settings bar is cropped such that some buttons cannot be seen properly.
- [x] Interface issue: when clicking on the settings bar, sometimes a red marker shows up on the screen
### Functionality
- [x] **Needs testing** - latency issues even with filter size of 1 (no filter), it seems to be slower and not very responsive than. could this be due to new graphics engine?
### Installation
- [ ] Installation: Step 4 warning after “dotnet build”:​ warning CS8618: Non-nullable event 'BalanceBoardDataReceived' must contain a non-null value when exiting constructor. Considerdeclaring the event as nullable. ​
---

## 🟡 Code Quality

- [x] Extract recording logic from `app.py` into `recording.py`
- [ ] Refactor remaining large code blocks in `app.py` into smaller functions
- [ ] add docstrings to all functions and classes for better maintainability

---

## 🟢 Developer Experience


### Add Logging Framework
- [x] Replace `print()` calls with Python's `logging` module
- [x] Use `DEBUG` for sensor data, `INFO` for state changes, `ERROR` for failures
- [x] Log to file at `~/.wiibble/wiibble.log` and stdout

### Add GitHub Actions CI Pipeline
- [x] Add workflow to lint Python (`ruff`) — runs on push to `develop`/`main`
- [ ] Add workflow to build the C# DLL (`dotnet build`)
- [x] Add workflow to run Python unit tests (`pytest`) — runs with coverage gate (≥80%)
- [ ] Add workflow to build Nuitka executable and archive as artifact

###  Add Unit Tests
- [x] Add tests for `parse_data()` using known raw byte arrays
- [x] Add tests for `calculate_coordinates()` with known inputs
- [x] Add tests for the moving average filter — fully testable without hardware
- [x] Add tests for CSV recording logic (`recording.py`) — fully testable without hardware
- [x] Use `pytest` as the test framework
- [x] Coverage gate enforced at ≥80% (currently 82%)

---

## 🟢 Project Structure
- [x] Split `_save_recording_csv` from `app.py` into `recording.py` for better separation of concerns and testability
- [ ] Further refactor `app.py` (e.g. `session.py`) for remaining logic
- [ ] Move C# interop code from `board_connection.py` into a dedicated `hardware_interface.py` module
- [ ] Add a `utils.py` for any shared helper functions that don't fit elsewhere
- [ ] Organise assets into subfolders (e.g. `assets/fonts/`, `assets/images/`) for better clarity



