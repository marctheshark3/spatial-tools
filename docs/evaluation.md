# Evaluation

The first evaluation asks whether the supplied geometry contract works and whether
the skill's launcher reaches it. It does not yet ask whether a language model
performs better with the skill.

## Reproduce

```sh
uv sync --locked
uv run pytest -q
uv run ruff check .
uv run python scripts/build_schema.py --check
uv run python scripts/evaluate.py
uv run python scripts/pilot.py
```

`tests/fixtures/cases.json` contains 30 authored requests with independent expected
answers and a rationale for each. The evaluation script reports exact case counts,
status counts, failures, and unsupported positive results. Unit tests additionally
cover rigid transforms, unit scaling, polygon holes, diagonal crossings, thin
walls between grid nodes, numeric rejection, live freshness, JSON parsing, CLI
exit codes, skill launch, and installer conflicts.

The initial observed environment (2026-10-10) used Python 3.14.4, Shapely 2.2.0,
and GEOS 3.14.1. The 30 cases passed: 9 supported, 8 blocked, 6 unknown, and
7 invalid, with zero unsupported positive results. See the checked-in fixtures
and commands rather than inferring a general reliability rate from that count.
The initial full suite passed 60 tests. CI repeats the checks on Python 3.10,
3.12, and 3.14; use the current run status for observations about those versions.

## Map-update pilot

![A clear 9 m route becomes blocked after the wall grows; replanning produces a clear 10 m route.](images/route-refresh.png)

The pilot invokes the actual skill launcher for every calculation and saves its
requests and results in ignored `eval-runs/runtime-pilot/`:

1. Plan a 9-unit grid route around the wall in `examples/plan-route.json`.
2. Check that returned route with the standalone continuous path operation.
3. Enlarge the wall and refresh the observation timestamp. The old route is blocked.
4. Plan again from the new scene. The shortest grid route is now 10 units.
5. Check the new returned route before relying on it.

The [visual walkthrough](visual-guide.md#refresh-the-map-and-replan) connects
this diagram to the commands, footprint, grid, and expected outcomes.

To exercise an installed skill instead of the source path:

```sh
uv run python scripts/pilot.py --skill ~/.agents/skills/spatial-reasoning
```

The initial pilot passed all five steps. This tests scene refresh, footprint
handling, planning, and tool invocation. It
does not drive a game, exercise visual perception, or measure skill activation
inside a fresh model session.

The initial local Codex app-server `skills/list` probe discovered the installed
skill with user scope and `enabled: true`. No model turn was run. To repeat that
check, start `codex app-server --stdio`, initialize a client, send the `initialized`
notification, and request `skills/list` with your workspace in `cwds` and
`forceReload: true`. Stop the local probe afterwards. A different harness must
check its own discovery mechanism.

## Agent evaluation still needed

Compare the same model and task budget under three conditions: ordinary
observations; explicit structured scene; structured scene plus this skill/runtime.
Reset each scene, repeat stochastic trials, and separately record success,
geometric violations, abstentions, calls, latency, and inference cost. Include
transformed and changed layouts, and a conventional planner for fully specified
maps. Keep expected answers unavailable to the model.

Positive activation examples include footprint clearance, a rotated static fit,
and a blocked-map route. Negative examples include an unambiguous named-button
click, a general writing request, and an olympiad proof. Confirm both explicit
`$spatial-reasoning` invocation and ordinary discovery in the actual harness.

Runtime correctness and schema/skill validation are prerequisites. They do not
establish that instructions improve agent decisions, that inferred coordinates are
accurate, or that an application controller successfully executes a route. Record
those as separate findings before adding a controller adapter or perception model.
