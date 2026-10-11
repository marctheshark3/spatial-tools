#!/usr/bin/env python3
"""Locate the separately packaged runtime without installing anything implicitly."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[3]
    local = (
        root
        / ".venv"
        / ("Scripts" if os.name == "nt" else "bin")
        / ("spatial-tools.exe" if os.name == "nt" else "spatial-tools")
    )
    executable = str(local) if local.is_file() else shutil.which("spatial-tools")
    if not executable:
        print(
            "spatial-tools runtime is missing. Clone "
            "https://github.com/marctheshark3/spatial-tools and run `uv sync --locked`, "
            "then install its skill symlink; or run `python -m pip install .` in that repo.",
            file=sys.stderr,
        )
        return 64
    os.execv(executable, [executable, *sys.argv[1:]])
    return 64


if __name__ == "__main__":
    raise SystemExit(main())
