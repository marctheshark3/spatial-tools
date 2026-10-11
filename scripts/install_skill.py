#!/usr/bin/env python3
"""Install a symlink without replacing an existing skill."""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target", type=Path, required=True, help="Agent skill discovery directory"
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    source = root / "skills" / "spatial-reasoning"
    target = args.target.expanduser().resolve() / source.name
    if target.is_symlink() and target.resolve() == source:
        print(f"Already installed: {target}")
        return 0
    if target.exists() or target.is_symlink():
        parser.error(f"refusing to replace existing skill: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.symlink_to(source, target_is_directory=True)
    print(f"Installed {target} -> {source}; reload your agent's skill list.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
