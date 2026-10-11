# Runtime operations

Call `scripts/spatial.py run request.json` or pipe JSON to `run -`. It emits JSON
only on stdout. `batch requests.json` accepts an array of requests. Use `schema`
to inspect the contract and `--version` to record the runtime version.

All operations use `schema_version: 1`, `operation`, `scene`, and `query`.

| Operation | Query fields |
|---|---|
| `validate_scene` | No operation-specific fields. |
| `relation` | Object IDs `a`, `b`; `predicate`: `distance`, `intersects`, or `covers`. |
| `fit` | Object IDs `item`, `container`; `margin`; optional `rotation_degrees` about item centroid, then `translation: [dx,dy]`. |
| `check_path` | `path`: array of 2D points; nonnegative disk `radius` and `margin`. |
| `plan` | `start`, `goal`, disk `radius`, `margin`; `grid` with `min`, `max`, positive `step`, and `max_nodes`. |

`distance` measures closest surfaces and includes an uncertainty interval.
Relation `intersects` and `covers` include contact. With nonzero uncertainty their
boolean topology is nominal and the status is `unknown`.

Fit and path checks require strictly more clearance than margin plus positional
uncertainty (and disk radius for motion), allowing the reported numerical tolerance.
Contact is blocked. The entire path is checked, including segments between points.

Planning uses a bounded four-connected grid. Start, goal, and bounds must align
with the step. Every edge and the final path are checked continuously. A grid with
no route returns `blocked` with grid-only scope; search-budget exhaustion is
`unknown`. Do not infer continuous-space impossibility from a grid result.

Read `status`, `result`, `reasons`, and `evidence` together:

- `supported` / exit 0: calculation supported in the provided model.
- `blocked` / exit 2: this placement/path or bounded-grid route fails.
- `unknown` / exit 3: insufficient, stale, uncertain, or budget-limited evidence.
- `invalid` / exit 64: malformed or unsupported input.

The launcher needs either the repository's `.venv/bin/spatial-tools` or an installed
`spatial-tools` executable. It does not install software or make network calls.
From a cloned repository, run `uv sync --locked` once to create that environment.
