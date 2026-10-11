# spatial-tools

Give an agent an explicit 2D scene, then check its spatial claims with geometry.
This project packages a Python runtime and a `spatial-reasoning` skill together.
The runtime is usable from any agent, CLI, or Python program.

It checks distance and overlap, static fit, continuous path clearance for a disk
footprint, and routes on a bounded four-connected grid. Every answer carries its
units, frame, observation time, uncertainty, and scene completeness.

## Try it

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/getting-started/installation/).

```sh
git clone https://github.com/marctheshark3/spatial-tools.git
cd spatial-tools
uv sync --locked
uv run spatial-tools run examples/clear-path.json
uv run spatial-tools run examples/blocked-path.json
uv run spatial-tools run examples/plan-route.json
uv run python scripts/pilot.py
```

`run` exits with 0 for `supported`, 2 for `blocked`, 3 for `unknown`, and 64 for
`invalid`. A blocked example deliberately exits with 2. JSON is always on stdout.
`batch` accepts an array of up to 100 requests and returns each result; its exit
code is 64 if any request is invalid, otherwise 0.

For a runtime-only installation, `python -m pip install .` also works. The skill
is distributed in this Git repository, separately from the Python wheel.

## Use the skill

After `uv sync --locked`, install a symlink to this checkout:

```sh
python scripts/install_skill.py --target ~/.agents/skills
```

For a harness configured to discover skills in `~/.codex/skills`, use that directory
as `--target` instead. The installer refuses to replace an existing skill. Reload
your agent's skill list after installation.

Example request:

> Use $spatial-reasoning to check this route. The frame is world, metres, x right
> and y up. The scene is complete and has zero coordinate uncertainty. A wall
> occupies [2,-1] to [4,1]. My circular footprint has radius 0.25 m and needs
> 0.1 m extra clearance. Can I travel from [0,1.4] to [6,1.4]?

For a live task, supply the observation timestamp and refresh the scene before
acting. The tool does not control a browser, game, robot, or machine. Existing
controllers remain responsible for observe–act–observe and authorization.

## Read a result

| Status | Meaning |
|---|---|
| `supported` | The specified calculation supports the result in this scene. A false relation can also be a supported answer. |
| `blocked` | This placement/path fails the clearance policy, or this grid has no route. |
| `unknown` | Missing evidence, stale observations, uncertain topology, or a search limit prevents a conclusion. |
| `invalid` | The request violates the scene contract. |

Boundary contact is blocked for fit and path clearance. Relation predicates
`intersects` and `covers` include contact. Distances measure the closest points
of the geometries, rather than their centres. Coordinates are never silently
converted or snapped. An explicitly replayed clock is for synthetic examples and
recorded evaluations; do not use it to make a live scene appear fresh.

## Scope and design

Use this for UI/canvas layouts, small game maps, 2D planning experiments, and
static CAD cross-sections. Supply application coordinates when available. Image
coordinates do not establish metric distances in the physical world.

The runtime uses [Shapely](https://shapely.readthedocs.io/en/stable/manual.html),
which provides planar geometry through GEOS. It is floating-point computation,
with a conservative numerical tolerance. It does not infer coordinates from
images, handle 3D geometry, model changing obstacles, prove geometry theorems,
or certify a physical system. A static fit is not an insertion path; a grid
route is not an optimal continuous route.

See [the scene contract](docs/scene-contract.md), [design rationale](docs/design.md),
[evaluation](docs/evaluation.md), and [contributing](CONTRIBUTING.md).

## License

Original code, documentation, and skill instructions are Apache-2.0. Dependencies
retain their own licenses: Shapely is BSD-3-Clause and its GEOS backend is LGPL.
See [LICENSE](LICENSE), [NOTICE](NOTICE), and
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). No research implementation,
model weights, or dataset has been incorporated.
