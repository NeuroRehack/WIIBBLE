# Contributing to WIIBBLE

Thank you for taking the time to contribute. This document covers everything you need to know before opening an issue or pull request.

---

## Table of Contents

- [Contributing to WIIBBLE](#contributing-to-wiibble)
  - [Table of Contents](#table-of-contents)
  - [Getting Set Up](#getting-set-up)
  - [Branching Strategy](#branching-strategy)
  - [Commit Messages](#commit-messages)
  - [Code Style](#code-style)
  - [Tests](#tests)
  - [Pull Request Process](#pull-request-process)
  - [Reporting Bugs](#reporting-bugs)

---

## Getting Set Up

Follow the full developer setup in [Docs/DEV.md](Docs/DEV.md). In short:

```powershell
git clone https://github.com/NeuroRehack/WIIBBLE.git
cd WIIBBLE
uv sync --extra dev
cd WiiBalanceBoardLibrary && dotnet build && cd ..
uv run wiibble --mock --mock-scenario sway # verify it runs without hardware
```

---

## Branching Strategy

| Branch | Purpose |
|---|---|
| `main` | Stable, release-tagged commits only |
| `develop` | Integration branch — all PRs target here |
| `feature/<name>` | New features and non-urgent improvements |
| `fix/<name>` | Bug fixes |
| `Docs/<name>` | Documentation-only changes |

Always branch from `develop`, never from `main`.

---

## Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>(<scope>): <short summary>

[optional body]

[optional footer: references issues]
```

Common types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`.

Examples:
```
feat(recording): add manual stop button during countdown
fix(ui): restore gear icon visibility after screen resize
docs(architecture): update module guide with `wiibble/analysis/analysis.py` changes
```

---

## Code Style

WIIBBLE uses [Ruff](https://github.com/astral-sh/ruff) for both linting and formatting, configured in `pyproject.toml`. Before pushing:

```powershell
uv run ruff check .              # lint
uv run ruff check . --fix        # auto-fix safe issues
uv run ruff format --check .     # verify formatting
uv run ruff format .             # apply formatting
```

CI will reject PRs that fail either check.

A few conventions to follow beyond what Ruff enforces:

- No magic numbers in `wiibble/app.py` or `wiibble/ui/ui.py` — add them to `wiibble/utils/constants.py`.
- No DPG or state imports in `wiibble/features/data_processing.py` — keep it a pure functional pipeline.
- Use `resource_path()` from `wiibble/utils/resources.py` for all asset access (required for Nuitka builds).
- Comments explain *why*, not *what*.

---

## Tests

Tests live in `tests/` and run with `pytest`. A coverage gate of **≥ 80%** is enforced for the testable modules (`wiibble/features/data_processing.py`, `wiibble/utils/state.py`, `wiibble/board/recording.py`). Hardware-dependent and UI code is excluded from the gate.

```powershell
uv run pytest -v                 # run all tests with coverage report
```

When adding a new feature:
- Add tests in `tests/` before or alongside the implementation.
- Use `MockHIDDevice` from `wiibble/board/mock_board.py` for anything that touches the sensor pipeline.
- Never add tests that require a physical Wii Balance Board to pass.

---

## Pull Request Process

1. Make sure `ruff check` and `pytest` both pass locally before opening a PR.
2. Target `develop`, not `main`.
3. Keep PRs focused — one logical change per PR makes review faster.
4. Fill in the PR description: what changed, why, and how to test it.
5. If the change affects the data pipeline, recording format, or analysis output, update the relevant doc in `Docs/`.
6. At least one approving review is required before merging.

---

## Reporting Bugs

Open a GitHub Issue with:
- WIIBBLE version (or commit hash)
- Windows version
- Steps to reproduce
- Expected vs actual behaviour
- Relevant lines from `~/.wiibble/wiibble.log`


