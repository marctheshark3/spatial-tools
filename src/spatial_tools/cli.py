"""JSON-only command interface; rejected inputs never become model evidence."""

from __future__ import annotations

import argparse
import json
import sys
from importlib.resources import files
from pathlib import Path

from . import __version__
from .engine import evaluate, response

EXIT_CODES = {"supported": 0, "blocked": 2, "unknown": 3, "invalid": 64}
MAX_INPUT_BYTES = 2_000_000


def unique_object(pairs: list[tuple]) -> dict:
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def reject_constant(value: str) -> None:
    raise ValueError(f"nonfinite JSON number: {value}")


def load(path: str):
    if path == "-":
        source = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    else:
        with Path(path).open("rb") as stream:
            source = stream.read(MAX_INPUT_BYTES + 1)
    if len(source) > MAX_INPUT_BYTES:
        raise ValueError(f"input exceeds {MAX_INPUT_BYTES} bytes")
    return json.loads(source, object_pairs_hook=unique_object, parse_constant=reject_constant)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate explicit 2D scenes; emit JSON evidence.")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("run", "batch"):
        sub = commands.add_parser(name)
        sub.add_argument("input", help="JSON file, or - for stdin")
    commands.add_parser("schema")
    args = parser.parse_args(argv)
    try:
        if args.command == "schema":
            output = json.loads(files("spatial_tools").joinpath("request.schema.json").read_text())
            exit_code = 0
        elif args.command == "run":
            output = evaluate(load(args.input))
            exit_code = EXIT_CODES[output["status"]]
        else:
            requests = load(args.input)
            if not isinstance(requests, list) or not 1 <= len(requests) <= 100:
                raise ValueError("batch input must contain 1 through 100 requests")
            results = [evaluate(request) for request in requests]
            output = {"schema_version": 1, "results": results}
            exit_code = 64 if any(r["status"] == "invalid" for r in results) else 0
    except (ValueError, OSError, RecursionError) as exc:
        output = response(None, "invalid", reasons=[str(exc)])
        exit_code = 64
    print(json.dumps(output, indent=2, allow_nan=False))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
