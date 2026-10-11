# Working on spatial-tools

This repository owns a small 2D geometry runtime and the spatial-reasoning skill
that calls it. Keep reusable geometry independent of any agent or browser driver.

- State units, coordinate frames, observation time, completeness, footprint, and
  uncertainty explicitly. A missing fact must not become a clearance claim.
- `supported` means supported by the supplied scene, never permission to act or a
  guarantee about the physical world. Preserve `blocked`, `unknown`, and `invalid`.
- Keep the public examples synthetic. Do not copy private wiki material, agent
  transcripts, credentials, application state, or local machine configuration.
- Own original code under Apache-2.0. Preserve dependency licenses and notices;
  do not import research implementations without reviewing their licenses.
- Use analytical fixtures and independent expected results for geometry checks.
  Run `uv run pytest`, `uv run ruff check .`, and the skill validator for changes
  to their respective surfaces. Record evaluation limits rather than claiming a
  skill improves a model from runtime tests alone.
- Keep the skill concise. Put the scene contract and tool details in references.
  Do not add browser control, theorem proving, 3D inference, or robotics execution
  to this runtime without a separately scoped design.
- Stage explicit paths. Do not overwrite an existing installed skill or publish
  model evaluation traces by default.
