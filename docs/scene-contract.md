# Scene contract, version 1

`spatial-tools schema` emits the JSON Schema. The runtime also validates geometry,
finite numbers, matching frames, observation time, and grid alignment. Use
`examples/` as executable requests.

Each request contains `schema_version: 1`, `operation`, `scene`, and `query`.
Unknown fields and duplicate JSON keys are rejected.

## Scene

- `frame`: `id`, `units` (`m`, `cm`, `mm`, or `px`), and `axes`
  (`x-right-y-up` or `x-right-y-down`). All coordinates share this Cartesian frame.
- `observed_at`: ISO 8601 timestamp with a timezone.
- `source`: `synthetic`, `application`, `measured`, or `inferred`.
- `complete`: whether the obstacle inventory covers the queried motion region.
  Path checks and planning require `true`; local relations and fit do not.
- `uncertainty`: nonnegative positional-error bound in frame units, or `null` for
  unknown. Zero is an explicit assertion, not a default. The bound must cover
  every supplied shape and queried coordinate, including shape-boundary errors.
- `objects`: at most 256 entries, each with a unique `id` and a `shape`.
  IDs beginning with `$` are reserved for runtime evidence.
  Every object is an obstacle for `check_path` and `plan`; omit decorations and
  the moving actor. There is no hidden traversable flag.
- Optional `workspace`: rectangle or polygon limiting motion. Without one the
  scene has no asserted outer boundary; the planner's grid still bounds search.

Shapes are `rectangle` (`min`, `max`), `polygon` (`vertices`, optional `holes`),
or `point` (`coordinates`). Rectangles and polygons must have positive area.
Polygon rings have at least three points, and at most 4096 vertices total per
shape. Self-intersections and invalid holes are rejected. Rings may be explicitly
closed or implicitly closed. Every point has exactly two finite coordinates,
each with magnitude at most 10,000,000; booleans and a Z coordinate are rejected.

## Shared query options

- `frame_id` and `units`, when supplied, must match the scene. No conversion occurs.
- `max_age_seconds`: nonnegative freshness limit, default 30 seconds.
- `as_of`: optional evaluation timestamp. Omit it for live work to use UTC now.
  Explicit clocks are for reproducible replay, not evidence that a scene is current.

Future or stale observations return `unknown`. No motion prediction is performed.
For clearance comparisons, the engine adds twice the positional-error bound to
the required clearance, conservatively allowing errors on both compared entities.
This assumes bounded geometric error, not an arbitrary topology change or an
unseen obstacle. Scene completeness remains a separate assertion.

The numerical tolerance is at least `1e-9` frame units, and at least `1e-12`
times the largest relevant coordinate magnitude. It is included in the result.
A margin is additional to the footprint; choose it in the same units. Shapely's
floating-point results are evidence about the supplied model, not exact proofs.

## Operations

| Operation | Required query fields | Result |
|---|---|---|
| `validate_scene` | None | Parsing, geometry, and freshness check; does not certify completeness or clear motion. |
| `relation` | `a`, `b`, `predicate` | `distance`, `intersects`, or `covers` between named objects. |
| `fit` | `item`, `container`, `margin` | Static containment and boundary clearance. |
| `check_path` | `path`, `radius`, `margin` | Continuous disk-footprint clearance along a polyline. |
| `plan` | `start`, `goal`, `radius`, `margin`, `grid` | A route on a bounded four-connected grid, followed by a full clearance check. |

`relation.distance` reports the nearest-surface distance and a positional-error
interval. `intersects` and `covers` include boundary contact. They return only a
nominal value with status `unknown` when uncertainty is nonzero. The interval
covers positional error; floating-point rounding remains subject to the numerical
limitations above.

`fit` optionally accepts `rotation_degrees` about the item's centroid, then
`translation: [dx, dy]`; both default to zero. Positive rotation follows numeric
Cartesian coordinates, so it appears clockwise in a y-down screen frame. The
container must be a polygon or rectangle. Boundary contact is blocked. Other
objects do not participate in this two-object fit question. No swept rotation,
assembly operation, or insertion path is inferred.

`check_path.path` contains 1 through 4096 points. A single point checks a stationary
footprint. All objects and any workspace boundary are obstacles. Contact is blocked,
including for radius zero. The result records each nearest obstacle clearance,
the required clearance, and the IDs that block it (`$workspace` for the boundary).
With no obstacles, minimum obstacle clearance is `null`, not infinity.

`plan.grid` requires `min`, `max`, `step`, and `max_nodes`. Bounds, start, and goal
must align with the grid; they are never snapped. Search includes boundary nodes,
but the scene's workspace and contact policy can exclude them. Grids contain at
most 100,000 nodes, with an expansion budget from 1 through 100,000 and a separate
400,000 edge-check limit. Grid bounds limit the centreline, not an asserted physical
wall. Supply a workspace when the footprint must remain inside a physical region.
No-route results concern this grid only. Budget exhaustion or a route exceeding
4096 vertices is `unknown`.

## Result

The result contains `schema_version`, `operation`, `status`, `result`, `reasons`,
and `evidence`. Evidence records the frame, timestamps, replay age, source,
completeness, uncertainty, numerical tolerance, and the model-only scope.
Operation-specific path/fit tolerances can be larger if queried coordinates are
larger than scene coordinates; use the tolerance recorded beside that measurement.

Use `supported`, `blocked`, `unknown`, and `invalid` as distinct outcomes. Read the
result value as well as the status. Refresh moving scenes before an action and
observe again afterwards; this tool supplies no application controls.
