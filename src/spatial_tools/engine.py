"""Small, explicit scene contract over Shapely's planar geometry operations."""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from shapely import affinity
from shapely.geometry import LineString, Point, Polygon, box
from shapely.geometry.base import BaseGeometry
from shapely.validation import explain_validity

MAX_COORDINATE = 10_000_000
MAX_OBJECTS = 256
MAX_VERTICES = 4096
MAX_GRID_NODES = 100_000
MAX_EDGE_CHECKS = 400_000
OPERATIONS = {"validate_scene", "relation", "fit", "check_path", "plan"}


class Invalid(ValueError):
    """An input cannot be interpreted according to the contract."""


def fields(value: Any, required: set[str], optional: set[str], label: str) -> dict:
    if not isinstance(value, dict):
        raise Invalid(f"{label} must be an object")
    missing = required - value.keys()
    extra = value.keys() - required - optional
    if missing or extra:
        raise Invalid(f"{label}: missing {sorted(missing)}, unexpected {sorted(extra)}")
    return value


def number(value: Any, label: str, *, nonnegative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise Invalid(f"{label} must be a finite number")
    try:
        result = float(value)
    except (OverflowError, ValueError) as exc:
        raise Invalid(f"{label} must be a finite number") from exc
    if not math.isfinite(result) or abs(result) > MAX_COORDINATE:
        raise Invalid(f"{label} must be finite and at most {MAX_COORDINATE} in magnitude")
    if nonnegative and result < 0:
        raise Invalid(f"{label} must be nonnegative")
    return result


def pair(value: Any, label: str) -> tuple[float, float]:
    if not isinstance(value, list) or len(value) != 2:
        raise Invalid(f"{label} must contain exactly two coordinates; Z is unsupported")
    return number(value[0], label), number(value[1], label)


def integer(value: Any, label: str, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise Invalid(f"{label} must be an integer from {low} through {high}")
    return value


def identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 128:
        raise Invalid(f"{label} must be a nonempty string of at most 128 characters")
    return value


def timestamp(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or "T" not in value:
        raise Invalid(f"{label} must be an ISO 8601 timestamp with a timezone")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise Invalid(f"{label} must be an ISO 8601 timestamp with a timezone") from exc
    if parsed.tzinfo is None:
        raise Invalid(f"{label} must include a timezone")
    return parsed.astimezone(timezone.utc)


def shape(value: Any, label: str) -> BaseGeometry:
    if not isinstance(value, dict):
        raise Invalid(f"{label} must be a shape object")
    kind = value.get("type")
    if kind == "rectangle":
        fields(value, {"type", "min", "max"}, set(), label)
        low, high = pair(value["min"], label), pair(value["max"], label)
        if low[0] >= high[0] or low[1] >= high[1]:
            raise Invalid(f"{label}: rectangle min must be strictly below max on both axes")
        geometry = box(*low, *high)
    elif kind == "point":
        fields(value, {"type", "coordinates"}, set(), label)
        geometry = Point(pair(value["coordinates"], label))
    elif kind == "polygon":
        fields(value, {"type", "vertices"}, {"holes"}, label)
        rings = [value["vertices"]]
        holes = value.get("holes", [])
        if not isinstance(holes, list):
            raise Invalid(f"{label}.holes must be an array")
        rings.extend(holes)
        vertices = []
        total = 0
        for ring in rings:
            if not isinstance(ring, list) or not 3 <= len(ring) <= MAX_VERTICES:
                raise Invalid(f"{label}: each ring needs 3 through {MAX_VERTICES} vertices")
            total += len(ring)
            if total > MAX_VERTICES:
                raise Invalid(f"{label}: too many vertices")
            vertices.append([pair(point, label) for point in ring])
        geometry = Polygon(vertices[0], vertices[1:])
    else:
        raise Invalid(f"{label}: supported shapes are rectangle, polygon, and point")
    if geometry.is_empty or not geometry.is_valid:
        raise Invalid(f"{label}: invalid geometry: {explain_validity(geometry)}")
    if isinstance(geometry, Polygon) and geometry.area <= 0:
        raise Invalid(f"{label}: polygon must have positive area")
    return geometry


@dataclass(frozen=True)
class Scene:
    frame: dict
    objects: dict[str, BaseGeometry]
    workspace: BaseGeometry | None
    observed_at: datetime
    as_of: datetime
    max_age: float
    source: str
    complete: bool
    uncertainty: float | None
    tolerance: float

    def evidence(self) -> dict:
        return {
            "frame": self.frame,
            "observed_at": self.observed_at.isoformat(),
            "as_of": self.as_of.isoformat(),
            "age_seconds": (self.as_of - self.observed_at).total_seconds(),
            "max_age_seconds": self.max_age,
            "source": self.source,
            "complete": self.complete,
            "uncertainty": self.uncertainty,
            "tolerance": self.tolerance,
            "scope": "Supplied 2D scene only; no permission to execute an action.",
        }


def read_scene(raw: Any, query: dict) -> Scene:
    fields(
        raw,
        {"frame", "observed_at", "source", "complete", "uncertainty", "objects"},
        {"workspace"},
        "scene",
    )
    frame = fields(raw["frame"], {"id", "units", "axes"}, set(), "scene.frame")
    identifier(frame["id"], "scene.frame.id")
    if frame["units"] not in ("m", "cm", "mm", "px"):
        raise Invalid("scene.frame.units must be m, cm, mm, or px; conversion is explicit")
    if frame["axes"] not in ("x-right-y-up", "x-right-y-down"):
        raise Invalid("scene.frame.axes must describe a supported Cartesian 2D frame")
    if query.get("frame_id", frame["id"]) != frame["id"]:
        raise Invalid("query.frame_id does not match scene.frame.id")
    if query.get("units", frame["units"]) != frame["units"]:
        raise Invalid("query.units does not match scene.frame.units")
    if raw["source"] not in ("synthetic", "application", "measured", "inferred"):
        raise Invalid("scene.source must be synthetic, application, measured, or inferred")
    if not isinstance(raw["complete"], bool):
        raise Invalid("scene.complete must be a boolean")
    uncertainty = raw["uncertainty"]
    if uncertainty is not None:
        uncertainty = number(uncertainty, "scene.uncertainty", nonnegative=True)
    observed_at = timestamp(raw["observed_at"], "scene.observed_at")
    as_of = (
        timestamp(query["as_of"], "query.as_of") if "as_of" in query else datetime.now(timezone.utc)
    )
    max_age = number(query.get("max_age_seconds", 30), "query.max_age_seconds", nonnegative=True)
    raw_objects = raw["objects"]
    if not isinstance(raw_objects, list) or len(raw_objects) > MAX_OBJECTS:
        raise Invalid(f"scene.objects must contain at most {MAX_OBJECTS} objects")
    objects = {}
    for obj in raw_objects:
        fields(obj, {"id", "shape"}, set(), "scene.objects entry")
        obj_id = identifier(obj["id"], "object.id")
        if obj_id.startswith("$"):
            raise Invalid("object IDs beginning with $ are reserved for runtime evidence")
        if obj_id in objects:
            raise Invalid(f"duplicate object ID: {obj_id}")
        objects[obj_id] = shape(obj["shape"], f"object {obj_id}")
    workspace = shape(raw["workspace"], "scene.workspace") if "workspace" in raw else None
    if workspace is not None and not isinstance(workspace, Polygon):
        raise Invalid("scene.workspace must be a rectangle or polygon")
    geometries = list(objects.values()) + ([workspace] if workspace is not None else [])
    scale = max([1.0] + [abs(x) for geom in geometries for x in geom.bounds])
    return Scene(
        frame,
        objects,
        workspace,
        observed_at,
        as_of,
        max_age,
        raw["source"],
        raw["complete"],
        uncertainty,
        max(1e-9, scale * 1e-12),
    )


def response(
    operation: str | None,
    status: str,
    result: Any = None,
    *,
    scene: Scene | None = None,
    reasons: list[str] | None = None,
) -> dict:
    return {
        "schema_version": 1,
        "operation": operation,
        "status": status,
        "result": result,
        "reasons": reasons or [],
        "evidence": scene.evidence() if scene else None,
    }


def unknown_reasons(scene: Scene, *, completeness: bool) -> list[str]:
    reasons = []
    age = (scene.as_of - scene.observed_at).total_seconds()
    if age < -1e-6:
        reasons.append("Observation is in the future relative to the evaluation clock.")
    if age > scene.max_age:
        reasons.append("Observation is stale; acquire a fresh scene before relying on it.")
    if scene.uncertainty is None:
        reasons.append("Coordinate uncertainty is unbounded or unknown.")
    if completeness and not scene.complete:
        reasons.append("Obstacle inventory is incomplete; clearance cannot be established.")
    return reasons


def object_by_id(scene: Scene, value: Any) -> BaseGeometry:
    identifier(value, "query object ID")
    if value not in scene.objects:
        raise Invalid(f"unknown object ID: {value}")
    return scene.objects[value]


COMMON_QUERY = {"frame_id", "units", "as_of", "max_age_seconds"}


def path_geometry(raw: Any) -> tuple[list[tuple[float, float]], BaseGeometry]:
    if not isinstance(raw, list) or not 1 <= len(raw) <= MAX_VERTICES:
        raise Invalid(f"query.path needs 1 through {MAX_VERTICES} 2D points")
    points = [pair(item, "query.path") for item in raw]
    # A one-point path still checks the footprint at that position.
    geometry = Point(points[0]) if len(set(points)) == 1 else LineString(points)
    return points, geometry


def path_measurements(scene: Scene, path: BaseGeometry, radius: float, margin: float) -> dict:
    required = radius + margin + 2 * (scene.uncertainty or 0)
    scale = max([1.0] + [abs(x) for x in path.bounds])
    tolerance = max(scene.tolerance, scale * 1e-12)
    clearances = {key: float(path.distance(geom)) for key, geom in scene.objects.items()}
    blocked_by = [key for key, distance in clearances.items() if distance <= required + tolerance]
    workspace_clearance = None
    if scene.workspace is not None:
        workspace_clearance = float(path.distance(scene.workspace.boundary))
        if not scene.workspace.covers(path) or workspace_clearance <= required + tolerance:
            blocked_by.append("$workspace")
    return {
        "clear": not blocked_by,
        "blocked_by": blocked_by,
        "obstacle_clearances": clearances,
        "minimum_obstacle_clearance": min(clearances.values()) if clearances else None,
        "workspace_clearance": workspace_clearance,
        "required_clearance": required,
        "tolerance": tolerance,
        "contact_policy": "Boundary contact is blocked, including a zero-radius footprint.",
    }


def relation(scene: Scene, query: dict) -> dict:
    fields(query, {"a", "b", "predicate"}, COMMON_QUERY, "query")
    a, b = object_by_id(scene, query["a"]), object_by_id(scene, query["b"])
    predicate = query["predicate"]
    if predicate not in ("distance", "intersects", "covers"):
        raise Invalid("query.predicate must be distance, intersects, or covers")
    reasons = unknown_reasons(scene, completeness=False)
    if reasons:
        return response("relation", "unknown", scene=scene, reasons=reasons)
    distance = float(a.distance(b))
    uncertainty = scene.uncertainty or 0
    if predicate == "distance":
        result = {
            "distance": distance,
            "distance_interval": [max(0.0, distance - 2 * uncertainty), distance + 2 * uncertainty],
        }
    else:
        nominal = bool(a.intersects(b) if predicate == "intersects" else a.covers(b))
        if uncertainty > 0:
            return response(
                "relation",
                "unknown",
                {"nominal_value": nominal},
                scene=scene,
                reasons=["Boolean topology is nominal only with nonzero uncertainty."],
            )
        result = {"value": nominal, "boundary_policy": "intersects and covers include contact"}
    return response("relation", "supported", result, scene=scene)


def fit(scene: Scene, query: dict) -> dict:
    fields(
        query,
        {"item", "container", "margin"},
        COMMON_QUERY | {"rotation_degrees", "translation"},
        "query",
    )
    item = object_by_id(scene, query["item"])
    container = object_by_id(scene, query["container"])
    if not isinstance(container, Polygon):
        raise Invalid("fit container must be a rectangle or polygon")
    margin = number(query["margin"], "query.margin", nonnegative=True)
    rotation = number(query.get("rotation_degrees", 0), "query.rotation_degrees")
    translation = pair(query.get("translation", [0, 0]), "query.translation")
    moved = affinity.translate(affinity.rotate(item, rotation, origin="centroid"), *translation)
    reasons = unknown_reasons(scene, completeness=False)
    if reasons:
        return response("fit", "unknown", scene=scene, reasons=reasons)
    clearance = float(moved.distance(container.boundary))
    required = margin + 2 * (scene.uncertainty or 0)
    scale = max([1.0] + [abs(x) for x in moved.bounds])
    tolerance = max(scene.tolerance, scale * 1e-12)
    fits = bool(container.covers(moved) and clearance > required + tolerance)
    result = {
        "fits": fits,
        "boundary_clearance": clearance,
        "required_clearance": required,
        "tolerance": tolerance,
        "transformed_bounds": list(moved.bounds),
        "rotation_degrees": rotation,
        "translation": list(translation),
        "scope": "Static placement only; no insertion or rotation sweep is checked.",
    }
    return response("fit", "supported" if fits else "blocked", result, scene=scene)


def check_path(scene: Scene, query: dict) -> dict:
    fields(query, {"path", "radius", "margin"}, COMMON_QUERY, "query")
    points, path = path_geometry(query["path"])
    radius = number(query["radius"], "query.radius", nonnegative=True)
    margin = number(query["margin"], "query.margin", nonnegative=True)
    reasons = unknown_reasons(scene, completeness=True)
    if reasons:
        return response("check_path", "unknown", scene=scene, reasons=reasons)
    result = path_measurements(scene, path, radius, margin)
    result.update({"path": [list(point) for point in points], "length": float(path.length)})
    return response(
        "check_path", "supported" if result["clear"] else "blocked", result, scene=scene
    )


def plan(scene: Scene, query: dict) -> dict:
    fields(query, {"start", "goal", "radius", "margin", "grid"}, COMMON_QUERY, "query")
    start, goal = pair(query["start"], "query.start"), pair(query["goal"], "query.goal")
    radius = number(query["radius"], "query.radius", nonnegative=True)
    margin = number(query["margin"], "query.margin", nonnegative=True)
    grid = fields(query["grid"], {"min", "max", "step", "max_nodes"}, set(), "query.grid")
    low, high = pair(grid["min"], "grid.min"), pair(grid["max"], "grid.max")
    step = number(grid["step"], "grid.step", nonnegative=True)
    budget = integer(grid["max_nodes"], "grid.max_nodes", 1, MAX_GRID_NODES)
    if step == 0 or low[0] >= high[0] or low[1] >= high[1]:
        raise Invalid("grid needs a positive step and increasing min/max coordinates")
    width, height = (high[0] - low[0]) / step, (high[1] - low[1]) / step
    if not all(math.isfinite(n) and n <= MAX_GRID_NODES for n in (width, height)):
        raise Invalid("grid dimensions exceed supported limits")
    if any(abs(n - round(n)) > 1e-7 for n in (width, height)):
        raise Invalid("grid bounds must align to step; no implicit snapping")
    dims = round(width) + 1, round(height) + 1
    if dims[0] * dims[1] > MAX_GRID_NODES:
        raise Invalid(f"grid can contain at most {MAX_GRID_NODES} nodes")

    def grid_index(point: tuple[float, float]) -> tuple[int, int]:
        indices = tuple((point[i] - low[i]) / step for i in (0, 1))
        if any(not math.isfinite(n) or abs(n - round(n)) > 1e-7 for n in indices):
            raise Invalid("start and goal must lie on grid nodes; no implicit snapping")
        result = round(indices[0]), round(indices[1])
        if not all(0 <= result[i] < dims[i] for i in (0, 1)):
            raise Invalid("start and goal must be inside the grid bounds")
        return result

    def coordinate(node: tuple[int, int]) -> tuple[float, float]:
        return low[0] + node[0] * step, low[1] + node[1] * step

    def heuristic(node: tuple[int, int]) -> int:
        return abs(node[0] - target[0]) + abs(node[1] - target[1])

    origin, target = grid_index(start), grid_index(goal)
    reasons = unknown_reasons(scene, completeness=True)
    if reasons:
        return response("plan", "unknown", scene=scene, reasons=reasons)
    for name, point in (("start", start), ("goal", goal)):
        measurements = path_measurements(scene, Point(point), radius, margin)
        if not measurements["clear"]:
            return response("plan", "blocked", {"endpoint": name, **measurements}, scene=scene)
    frontier = [(heuristic(origin), 0, origin)]
    cost = {origin: 0}
    parents = {}
    visited = set()
    edge_checks = 0
    while frontier:
        _, current_cost, node = heapq.heappop(frontier)
        if node in visited or current_cost != cost[node]:
            continue
        if len(visited) >= budget:
            return response(
                "plan",
                "unknown",
                {"expanded_nodes": len(visited)},
                scene=scene,
                reasons=["Search budget exhausted; no feasibility conclusion."],
            )
        visited.add(node)
        if node == target:
            route = [node]
            while route[-1] != origin:
                route.append(parents[route[-1]])
            if len(route) > MAX_VERTICES:
                return response(
                    "plan",
                    "unknown",
                    scene=scene,
                    reasons=["Route exceeds the supported path vertex limit."],
                )
            points = [list(coordinate(n)) for n in reversed(route)]
            _, path = path_geometry(points)
            validation = path_measurements(scene, path, radius, margin)
            if not validation["clear"]:
                return response(
                    "plan",
                    "unknown",
                    scene=scene,
                    reasons=["Final route failed continuous clearance validation."],
                )
            return response(
                "plan",
                "supported",
                {
                    "path": points,
                    "length": float(path.length),
                    "expanded_nodes": len(visited),
                    "edge_checks": edge_checks,
                    "validation": validation,
                    "scope": "Shortest path on this bounded four-connected grid only.",
                },
                scene=scene,
            )
        for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1)):
            nxt = node[0] + dx, node[1] + dy
            if not all(0 <= nxt[i] < dims[i] for i in (0, 1)) or nxt in visited:
                continue
            new_cost = current_cost + 1
            if new_cost >= cost.get(nxt, math.inf):
                continue
            edge_checks += 1
            if edge_checks > MAX_EDGE_CHECKS:
                return response(
                    "plan", "unknown", scene=scene, reasons=["Edge-check budget exhausted."]
                )
            edge = LineString([coordinate(node), coordinate(nxt)])
            if not path_measurements(scene, edge, radius, margin)["clear"]:
                continue
            cost[nxt] = new_cost
            parents[nxt] = node
            heapq.heappush(frontier, (new_cost + heuristic(nxt), new_cost, nxt))
    return response(
        "plan",
        "blocked",
        {
            "expanded_nodes": len(visited),
            "scope": "No route on the supplied grid; continuous routes may still exist.",
        },
        scene=scene,
    )


def evaluate(request: Any) -> dict:
    """Validate and evaluate one request; return a JSON-serializable result."""
    operation = request.get("operation") if isinstance(request, dict) else None
    try:
        fields(request, {"schema_version", "operation", "scene", "query"}, set(), "request")
        if type(request["schema_version"]) is not int or request["schema_version"] != 1:
            raise Invalid("schema_version must be integer 1")
        if not isinstance(operation, str) or operation not in OPERATIONS:
            raise Invalid(f"operation must be one of {sorted(OPERATIONS)}")
        query = request["query"]
        if not isinstance(query, dict):
            raise Invalid("query must be an object")
        scene = read_scene(request["scene"], query)
        if operation == "validate_scene":
            fields(query, set(), COMMON_QUERY, "query")
            reasons = unknown_reasons(scene, completeness=False)
            return response(
                operation,
                "unknown" if reasons else "supported",
                {"object_count": len(scene.objects)},
                scene=scene,
                reasons=reasons,
            )
        return {"relation": relation, "fit": fit, "check_path": check_path, "plan": plan}[
            operation
        ](scene, query)
    except Invalid as exc:
        return response(
            operation if isinstance(operation, str) else None, "invalid", reasons=[str(exc)]
        )
