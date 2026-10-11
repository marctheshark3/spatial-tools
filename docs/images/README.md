# Documentation images

The four illustrations are original Apache-2.0 material, generated with
Matplotlib from this repository's synthetic JSON examples and checked runtime
results. Geometry plots use equal axis scales. The workflow is a schematic.
No stock images, research figures, or private scenes are included.

| Illustration | Vector | PNG |
|---|---|---|
| Workflow | [SVG](workflow.svg) | [PNG](workflow.png) |
| Footprint clearance | [SVG](path-clearance.svg) | [PNG](path-clearance.png) |
| Rotated static fit | [SVG](rotated-fit.svg) | [PNG](rotated-fit.png) |
| Map refresh and replanning | [SVG](route-refresh.svg) | [PNG](route-refresh.png) |

SVGs retain editable text and scale for export. The documentation embeds PNGs
for consistent type across viewers; these are also portable copies for sharing. Labels and shapes come from
[scripts/render_diagrams.py](../../scripts/render_diagrams.py), which checks the
expected runtime statuses before drawing.

To regenerate both formats from the repository root:

```sh
uv run --group docs python scripts/render_diagrams.py
```

To check that the SVGs match the current examples and locked documentation tools:

```sh
uv run --group docs python scripts/render_diagrams.py --check
```

The optional `docs` dependency group adds the renderer; it is not a runtime or
skill requirement. The locked versions are in `uv.lock`. Edit the source or
examples and regenerate the images instead of adjusting plotted coordinates by
hand.
