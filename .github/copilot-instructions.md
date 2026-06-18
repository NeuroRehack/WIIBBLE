# WIIBBLE — Copilot context

WIIBBLE is a Windows-first DearPyGui clinical desktop app that reads Nintendo Wii Balance Board HID data, visualises centre of pressure in real time, records sessions to CSV, and runs an offline posturographic analysis pipeline.

## Layout

- `src/wiibble/` — Python package (`app.py` session loop, `ui/` rendering, `features/data_processing.py` sensor pipeline, `board/` hardware, `analysis/` calibration and features, `cli/` offline tools)
- `WiiBalanceBoardLibrary/` — C# DLL for the one-time Bluetooth handshake (Windows only)
- `tests/` — pytest suite; use `MockHIDDevice` for sensor tests, never a physical board
- `docs/dev/` — developer setup, architecture, ADRs, pipeline notes
- `docs/user/manual.md` — clinician-facing manual

## Dependency direction

`app.py` orchestrates; `ui/` draws; `features/` and `board/` contain testable logic with no UI imports. Do not import UI from backend modules.

## Tooling

- Package manager: `uv` (`uv sync --extra dev && uv pip install -e .`)
- Task runner: `just` (`just lint`, `just test`, `just coverage`, `just check`)
- Lint/format: ruff (configured in `pyproject.toml`, vendored `code_descriptors_postural_control` excluded)
- Tests: pytest with ≥ 80% coverage gate on `data_processing`, `state`, and `recording`

## Constraints

- Python 3.11 or 3.12 only (pythonnet)
- Do not edit vendored `src/code_descriptors_postural_control/`
- Real hardware and Nuitka packaging are Windows-only; Linux supports mock mode and unit tests
- Settings persist at `~/.wiibble/settings.json`; override in tests with `WIIBBLE_SETTINGS_PATH`

## Docs

- Setup: `docs/dev/setup.md`
- Architecture: `docs/dev/architecture.md`
- Contributing: `CONTRIBUTING.md`
