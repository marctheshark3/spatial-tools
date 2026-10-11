#!/usr/bin/env python3
"""Build the published JSON Schema; semantic geometry checks remain in the runtime."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def obj(properties: dict, required: list[str] | None = None) -> dict:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties) if required is None else required,
        "additionalProperties": False,
    }


def ref(name: str) -> dict:
    return {"$ref": f"#/$defs/{name}"}


def schema() -> dict:
    num = {"type": "number", "minimum": -10_000_000, "maximum": 10_000_000}
    positive = {**num, "minimum": 0}
    name = {"type": "string", "minLength": 1, "maxLength": 128}
    instant = {"type": "string", "format": "date-time"}
    common = {
        "frame_id": name,
        "units": {"enum": ["m", "cm", "mm", "px"]},
        "as_of": instant,
        "max_age_seconds": positive,
    }
    defs = {
        "pair": {"type": "array", "items": num, "minItems": 2, "maxItems": 2},
        "ring": {"type": "array", "items": ref("pair"), "minItems": 3, "maxItems": 4096},
        "rectangle": obj({"type": {"const": "rectangle"}, "min": ref("pair"), "max": ref("pair")}),
        "point": obj({"type": {"const": "point"}, "coordinates": ref("pair")}),
        "polygon": obj(
            {
                "type": {"const": "polygon"},
                "vertices": ref("ring"),
                "holes": {"type": "array", "items": ref("ring"), "maxItems": 1365},
            },
            ["type", "vertices"],
        ),
        "shape": {"oneOf": [ref("rectangle"), ref("point"), ref("polygon")]},
        "areaShape": {"oneOf": [ref("rectangle"), ref("polygon")]},
        "frame": obj(
            {
                "id": name,
                "units": common["units"],
                "axes": {"enum": ["x-right-y-up", "x-right-y-down"]},
            }
        ),
        "grid": obj(
            {
                "min": ref("pair"),
                "max": ref("pair"),
                "step": {**positive, "exclusiveMinimum": 0},
                "max_nodes": {"type": "integer", "minimum": 1, "maximum": 100_000},
            }
        ),
    }
    defs["scene"] = obj(
        {
            "frame": ref("frame"),
            "observed_at": instant,
            "source": {"enum": ["synthetic", "application", "measured", "inferred"]},
            "complete": {"type": "boolean"},
            "uncertainty": {"anyOf": [positive, {"type": "null"}]},
            "objects": {
                "type": "array",
                "maxItems": 256,
                "items": obj({"id": name, "shape": ref("shape")}),
            },
            "workspace": ref("areaShape"),
        },
        ["frame", "observed_at", "source", "complete", "uncertainty", "objects"],
    )
    queries = {
        "validate_scene": ({}, []),
        "relation": (
            {"a": name, "b": name, "predicate": {"enum": ["distance", "intersects", "covers"]}},
            ["a", "b", "predicate"],
        ),
        "fit": (
            {
                "item": name,
                "container": name,
                "margin": positive,
                "rotation_degrees": num,
                "translation": ref("pair"),
            },
            ["item", "container", "margin"],
        ),
        "check_path": (
            {
                "path": {"type": "array", "items": ref("pair"), "minItems": 1, "maxItems": 4096},
                "radius": positive,
                "margin": positive,
            },
            ["path", "radius", "margin"],
        ),
        "plan": (
            {
                "start": ref("pair"),
                "goal": ref("pair"),
                "radius": positive,
                "margin": positive,
                "grid": ref("grid"),
            },
            ["start", "goal", "radius", "margin", "grid"],
        ),
    }
    for operation, (properties, required) in queries.items():
        defs[operation + "Query"] = obj({**common, **properties}, required)
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://github.com/marctheshark3/spatial-tools/schema/request-v1",
        "title": "spatial-tools request, version 1",
        "description": "Structural contract; runtime also checks planar geometry and evidence.",
        **obj(
            {
                "schema_version": {"type": "integer", "const": 1},
                "operation": {"enum": list(queries)},
                "scene": ref("scene"),
                "query": {"type": "object"},
            }
        ),
        "oneOf": [
            {"properties": {"operation": {"const": operation}, "query": ref(operation + "Query")}}
            for operation in queries
        ],
        "$defs": defs,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    path = Path(__file__).resolve().parents[1] / "src/spatial_tools/request.schema.json"
    content = json.dumps(schema(), indent=2) + "\n"
    if args.check:
        if not path.exists() or path.read_text() != content:
            parser.error("request.schema.json is out of date; run scripts/build_schema.py")
    else:
        path.write_text(content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
