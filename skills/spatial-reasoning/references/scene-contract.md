# Building a request

The authoritative contract is `docs/scene-contract.md` in the spatial-tools
repository. `python ../scripts/spatial.py schema` emits its machine-readable form;
resolve that script relative to this reference's directory.

```json
{
  "schema_version": 1,
  "operation": "check_path",
  "scene": {
    "frame": {"id": "world", "units": "m", "axes": "x-right-y-up"},
    "observed_at": "2026-10-10T12:00:00Z",
    "source": "synthetic",
    "complete": true,
    "uncertainty": 0,
    "objects": [
      {"id": "wall", "shape": {"type": "rectangle", "min": [2,-1], "max": [4,1]}}
    ]
  },
  "query": {
    "as_of": "2026-10-10T12:00:01Z",
    "path": [[0,1.4], [6,1.4]],
    "radius": 0.25,
    "margin": 0.1
  }
}
```

This example replays a synthetic scene. For live work use a fresh `observed_at`
and omit `as_of` so the runtime uses UTC now. The default age limit is 30 seconds;
set `max_age_seconds` to a task-appropriate limit when needed.

All points contain exactly two finite coordinates in one Cartesian frame. Units
are `m`, `cm`, `mm`, or `px`; axes are `x-right-y-up` or `x-right-y-down`.
`frame_id` and `units` in a query, when present, must match the scene.

Shapes are rectangle (`min`, `max`), polygon (`vertices`, optional `holes`), or
point (`coordinates`). Objects have unique IDs. Invalid polygons and Z coordinates
are rejected. In path checks, every listed object is an obstacle; omit the moving
actor. An optional polygon/rectangle `workspace` supplies an outer boundary.

`uncertainty` bounds positional and shape-boundary error in frame units. Zero must
be justified; use `null` for unknown. Clearance adds twice this bound to allow
errors on both compared entities. `complete` asserts obstacle coverage in the
motion region. It must be true to establish a clear path. Neither field detects
missing obstacles automatically.
