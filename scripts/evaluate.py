#!/usr/bin/env python3
"""Score synthetic geometry cases against independent, hand-derived expectations."""

from __future__ import annotations

import json
import math
from pathlib import Path

from spatial_tools import evaluate


def differences(actual: dict, expected: dict) -> list[str]:
    errors = []
    for path, value in expected.items():
        found = actual
        try:
            for key in path.split("."):
                found = found[int(key)] if isinstance(found, list) else found[key]
        except (KeyError, IndexError, TypeError, ValueError):
            errors.append(f"missing {path}")
            continue
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            matches = (
                isinstance(found, (int, float))
                and not isinstance(found, bool)
                and math.isclose(found, value, rel_tol=1e-10, abs_tol=1e-9)
            )
        else:
            matches = found == value
        if not matches:
            errors.append(f"{path}: expected {value!r}, got {found!r}")
    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    cases = json.loads((root / "tests/fixtures/cases.json").read_text())
    failures = []
    false_clearance = 0
    counts = dict.fromkeys(("supported", "blocked", "unknown", "invalid"), 0)
    for case in cases:
        actual = evaluate(case["request"])
        counts[actual["status"]] += 1
        errors = differences(actual, case["expected"])
        if errors:
            failures.append({"id": case["id"], "errors": errors})
        if actual["status"] == "supported" and case["expected"]["status"] != "supported":
            false_clearance += 1
    print(
        json.dumps(
            {
                "cases": len(cases),
                "passed": len(cases) - len(failures),
                "statuses": counts,
                "unsupported_positive_results": false_clearance,
                "failures": failures,
                "scope": "Synthetic runtime checks; not a model capability benchmark.",
            },
            indent=2,
        )
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
