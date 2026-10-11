# Design

A skill supplies the decision workflow: identify the spatial question, build the
smallest sufficient scene, call a tool, inspect its evidence, and refresh the scene
before action. A runtime supplies repeatable calculations. Keeping them in one
repository avoids separate releases drifting apart while retaining a neutral CLI
and Python API.

The scene is an explicit contract rather than an agent's informal mental picture.
Missing uncertainty is invalid; explicitly unknown uncertainty is `unknown`.
Incomplete obstacle coverage cannot support a clear-path claim. A false predicate
is still a valid answer to a relation question. None of these outcomes grants
execution permission.

Path checks use distance from the entire centreline to every obstacle. Comparing
that distance to disk radius plus clearance accounts for the footprint without
approximating it with a polygon or sampling only a few points. Workspace edges
receive the same clearance treatment. This implements the configuration-space
idea of expanding obstacles by the footprint; see
[LaValle, Planning Algorithms, configuration spaces](https://lavalle.pl/planning/node161.html).

The planner uses A* with Manhattan distance on a four-connected grid. Each edge
is checked continuously, and the returned route is checked again. This prevents
thin obstacles being skipped between grid nodes. Failure applies to the supplied
grid; it does not prove that no continuous route exists. Search limits return
`unknown`.

Shapely/GEOS supplies floating-point 2D geometry. The engine never repairs invalid
polygons or discards a third coordinate. These choices make input errors visible.
See [Shapely's coordinate model](https://shapely.readthedocs.io/en/stable/manual.html)
and [GEOS's Cartesian and precision limits](https://libgeos.org/usage/faq/).

The first version intentionally omits MCP and controller adapters. Its CLI is
already callable by agents with shell tools, and its Python function can back an
adapter later. Add an adapter when a real integration establishes the need; it
must preserve the same scene and result contracts.

No 3D reconstruction, learned geometry, theorem prover, or research implementation
is needed for this first use case. Such systems answer different questions and
would bring separate validation, dependency, and licensing requirements.
