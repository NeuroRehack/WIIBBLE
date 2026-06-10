"""Print the project version from pyproject.toml (single source of truth)."""

from __future__ import annotations

import tomllib
from pathlib import Path


def read_version(pyproject_path: Path | None = None) -> str:
    path = pyproject_path or Path(__file__).resolve().parent.parent / "pyproject.toml"
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return data["project"]["version"]


def main() -> None:
    print(read_version())


if __name__ == "__main__":
    main()
