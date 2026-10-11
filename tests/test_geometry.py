from __future__ import annotations

import copy
import importlib.util
import json
import math
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from spatial_tools import evaluate

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "tests/fixtures/cases.json").read_text())
SPEC = importlib.util.spec_from_file_location("benchmark", ROOT / "scripts/evaluate.py")
BENCHMARK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BENCHMARK)


def example(name="clear-path"):
    return json.loads((ROOT / "examples" / f"{name}.json").read_text())


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_analytical_case(case):
    actual = evaluate(case["request"])
    assert not BENCHMARK.differences(actual, case["expected"])
    json.dumps(actual, allow_nan=False)


def test_schema_accepts_supported_examples_and_validates_its_own_structure():
    schema = json.loads((ROOT / "src/spatial_tools/request.schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    for path in (ROOT / "examples").glob("*.json"):
        validator.validate(json.loads(path.read_text()))


def test_rigid_transform_preserves_clearance_and_decision():
    # 90-degree rotation plus translation: independent transformation arithmetic.
    request = example()
    baseline = evaluate(request)

    def transform(p):
        return [10 - p[1], -4 + p[0]]

    wall = request["scene"]["objects"][0]["shape"]
    corners = [transform(p) for p in ([2, -1], [4, -1], [4, 1], [2, 1])]
    wall.clear()
    wall.update({"type": "polygon", "vertices": corners})
    request["query"]["path"] = [transform(p) for p in request["query"]["path"]]
    actual = evaluate(request)
    assert actual["status"] == baseline["status"]
    assert actual["result"]["minimum_obstacle_clearance"] == pytest.approx(0.4)


def test_units_rescale_a_scene_without_changing_the_decision():
    request = example()
    request["scene"]["frame"]["units"] = "cm"
    wall = request["scene"]["objects"][0]["shape"]
    wall["min"] = [200, -100]
    wall["max"] = [400, 100]
    request["query"].update(path=[[0, 140], [600, 140]], radius=25, margin=10)
    actual = evaluate(request)
    assert actual["status"] == "supported"
    assert actual["result"]["minimum_obstacle_clearance"] == pytest.approx(40)


def test_polygon_hole_is_free_space_but_its_edges_are_obstacles():
    request = example()
    request["scene"]["objects"][0]["shape"] = {
        "type": "polygon",
        "vertices": [[-5, -5], [5, -5], [5, 5], [-5, 5]],
        "holes": [[[-2, -2], [2, -2], [2, 2], [-2, 2]]],
    }
    request["query"]["path"] = [[-1, 0], [1, 0]]
    assert evaluate(request)["status"] == "supported"
    request["query"]["path"] = [[-1, 0], [3, 0]]
    assert evaluate(request)["status"] == "blocked"


def test_diagonal_crossing_is_checked_between_vertices():
    request = example()
    request["scene"]["objects"][0]["shape"] = {
        "type": "rectangle",
        "min": [2.9, 2.9],
        "max": [3.1, 3.1],
    }
    request["query"]["path"] = [[0, 0], [6, 6]]
    assert evaluate(request)["status"] == "blocked"


def test_planner_cannot_skip_a_thin_wall_between_nodes():
    request = example("plan-route")
    request["scene"].pop("workspace")
    request["scene"]["objects"][0]["shape"] = {
        "type": "rectangle",
        "min": [0.24, -1],
        "max": [0.26, 1],
    }
    request["query"].update(
        start=[0, 0],
        goal=[0.5, 0],
        radius=0,
        margin=0,
        grid={"min": [0, 0], "max": [0.5, 0.5], "step": 0.5, "max_nodes": 10},
    )
    assert evaluate(request)["status"] == "blocked"


def test_returned_route_has_independently_checked_analytical_clearance():
    result = evaluate(example("plan-route"))
    assert result["status"] == "supported"
    points = result["result"]["path"]
    for a, b in zip(points, points[1:], strict=False):
        assert abs(a[0] - b[0]) + abs(a[1] - b[1]) == pytest.approx(0.5)
        # Every horizontal/vertical edge near the wall stays outside its expanded bounds.
        if a[1] == b[1] and max(a[0], b[0]) >= 2 and min(a[0], b[0]) <= 4:
            assert abs(a[1]) >= 1.5
        if a[0] == b[0] and max(a[1], b[1]) >= -1 and min(a[1], b[1]) <= 1:
            assert a[0] <= 1.5 or a[0] >= 4.5
    # Feed the actual plan into the independently usable path operation as well.
    check = example()
    check["query"]["path"] = points
    assert evaluate(check)["status"] == "supported"


@pytest.mark.parametrize("value", [True, float("nan"), float("inf"), -1, 10**1000])
def test_footprint_numbers_must_be_finite_nonnegative_real_values(value):
    request = example()
    request["query"]["radius"] = value
    assert evaluate(request)["status"] == "invalid"


def test_query_whole_path_tolerance_accounts_for_large_coordinates():
    request = example()
    request["scene"]["objects"] = []
    request["query"]["path"] = [[9_000_000, 0], [9_000_001, 0]]
    result = evaluate(request)
    assert result["status"] == "supported"
    assert math.isclose(result["result"]["tolerance"], 9_000_001e-12)


def test_live_clock_does_not_replay_a_stale_fixture_implicitly():
    request = example()
    request["scene"]["observed_at"] = "2000-01-01T00:00:00Z"
    request["query"].pop("as_of")
    assert evaluate(request)["status"] == "unknown"


def test_unknown_fields_and_missing_uncertainty_are_visible_errors():
    request = example()
    request["query"]["safe"] = True
    assert evaluate(request)["status"] == "invalid"
    request = example()
    request["scene"].pop("uncertainty")
    assert evaluate(request)["status"] == "invalid"


def test_scene_validation_is_not_a_claim_of_obstacle_completeness():
    request = example()
    request.update(operation="validate_scene", query={"as_of": "2026-10-10T12:00:01Z"})
    request["scene"]["complete"] = False
    result = evaluate(request)
    assert result["status"] == "supported"
    assert result["evidence"]["complete"] is False


def test_zero_radius_cannot_touch_an_obstacle():
    request = example()
    request["query"].update(path=[[0, 1], [6, 1]], radius=0, margin=0)
    assert evaluate(request)["status"] == "blocked"


def test_unknown_geometry_does_not_mutate_the_request():
    request = example()
    prior = copy.deepcopy(request)
    evaluate(request)
    assert request == prior


def test_object_ids_cannot_collide_with_runtime_boundary_evidence():
    request = example()
    request["scene"]["objects"][0]["id"] = "$workspace"
    assert evaluate(request)["status"] == "invalid"
