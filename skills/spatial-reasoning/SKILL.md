---
name: spatial-reasoning
description: Check practical 2D spatial questions using explicit coordinates and geometry tools. Use for fit, nearest distance, overlap, clearance, disk-footprint motion, and routes in layouts, canvases, game maps, or planar CAD sections. Especially useful when a spatial claim would affect an action. Do not use for ordinary named-button clicks, geometry theorem proofs, geometric machine learning, or 3D reconstruction.
---

# Spatial reasoning

Turn a spatial question into a small scene and a reproducible calculation. A
supported calculation applies to the supplied model; it does not authorize action.

## Establish the scene

1. Identify the requested decision: relation, static placement, proposed path, or
   route search. Use the simplest applicable operation.
2. Prefer application state and native coordinates over estimated image geometry.
   Record the frame, axis direction, units, observation timestamp, source,
   positional-error bound, and whether obstacle coverage is complete.
3. Include the relevant obstacle shapes, any workspace boundary, the moving disk's
   radius, and the requested margin. Keep pixels and physical units distinct.
   A rectangular actor needs a justified enclosing disk for motion checks, or a
   more suitable tool; do not silently treat it as a point.
4. If evidence is missing, obtain it or use an explicit `null` uncertainty /
   incomplete scene and report `unknown`. Do not invent coordinates, mark an
   inferred boundary exact, or manufacture freshness with a replay clock.

Read [references/scene-contract.md](references/scene-contract.md) before building
your first request. Read [references/tools.md](references/tools.md) for the
operation fields, result statuses, and invocation details.

## Calculate and inspect

Write a version-1 JSON request to a temporary file, then run:

```sh
python /path/to/spatial-reasoning/scripts/spatial.py run /path/to/request.json
```

Replace the skill path with this skill's actual installed path. The launcher uses
the repository's virtual environment or an installed `spatial-tools` command.
If the runtime is missing, follow the setup instruction it prints; do not replace
the calculation with an unsupported clearance claim.

- Read the JSON even when the command exits nonzero: `blocked` exits 2,
  `unknown` exits 3, and `invalid` exits 64. Correct invalid requests explicitly.
- Inspect the result value, units, frame, freshness, required clearance, tolerance,
  and blocking objects. A supported false relation is a valid negative answer.
- For planning, inspect the returned route and its continuous validation. A failed
  grid search does not prove that every possible route is blocked.
- A fit result checks one static placement. It does not check insertion, rotating
  through nearby objects, or travel to that placement.
- If tools and observations conflict, refresh the scene and check the contract.
  Explain remaining uncertainty rather than selecting a convenient answer.

## Use the answer

Report the decision, the relevant measurement and clearance threshold, the scene
assumptions, and any limits. Keep `unknown` distinct from `blocked`.

Before an authorized action, refresh changing state and recheck its next bounded
step. Use the existing browser/game/robot controller for action, then observe again.
This skill adds geometric evidence to that controller's workflow.
