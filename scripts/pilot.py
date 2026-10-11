#!/usr/bin/env python3
"""Exercise the skill launcher across a synthetic map update; no action controller."""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill", type=Path, default=root / "skills/spatial-reasoning")
    parser.add_argument("--output", type=Path, default=root / "eval-runs/runtime-pilot")
    args = parser.parse_args()
    output = args.output.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    launcher = args.skill.expanduser().resolve() / "scripts/spatial.py"
    checks = []

    def run(name: str, request: dict, expected_status: str, expected_length=None) -> dict:
        path = output / (name + ".request.json")
        path.write_text(json.dumps(request, indent=2) + "\n")
        process = subprocess.run(
            [sys.executable, str(launcher), "run", str(path)],
            text=True,
            capture_output=True,
            check=False,
        )
        if process.stderr:
            raise RuntimeError(process.stderr)
        result = json.loads(process.stdout)
        (output / (name + ".result.json")).write_text(process.stdout)
        if result["status"] != expected_status:
            raise RuntimeError(f"{name}: expected {expected_status}, got {result['status']}")
        if expected_length is not None and result["result"]["length"] != expected_length:
            raise RuntimeError(f"{name}: unexpected route length")
        checks.append({"step": name, "status": result["status"], "exit_code": process.returncode})
        return result

    original = json.loads((root / "examples/plan-route.json").read_text())
    planned = run("01-plan", original, "supported", 9)
    route = planned["result"]["path"]
    follow = copy.deepcopy(original)
    follow["operation"] = "check_path"
    follow["query"] = {
        "as_of": original["query"]["as_of"],
        "path": route,
        "radius": 0.25,
        "margin": 0.1,
    }
    run("02-validate-route", follow, "supported", 9)

    changed = copy.deepcopy(follow)
    changed["scene"]["objects"][0]["shape"].update(min=[2, -1.6], max=[4, 1.6])
    changed["scene"]["observed_at"] = "2026-10-10T12:00:02Z"
    changed["query"]["as_of"] = "2026-10-10T12:00:03Z"
    run("03-map-changed-old-route", changed, "blocked")

    replan = copy.deepcopy(original)
    replan["scene"] = changed["scene"]
    replan["query"]["as_of"] = changed["query"]["as_of"]
    refreshed = run("04-replan", replan, "supported", 10)
    changed["query"]["path"] = refreshed["result"]["path"]
    run("05-validate-new-route", changed, "supported", 10)
    summary = {
        "steps": checks,
        "passed": len(checks),
        "scope": "Skill launcher/runtime integration on a synthetic map; no model comparison.",
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
