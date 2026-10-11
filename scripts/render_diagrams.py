#!/usr/bin/env python3
"""Render documentation figures from executable scenes and checked runtime results."""

from __future__ import annotations

import argparse
import copy
import io
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch, Polygon, Rectangle
from shapely import affinity
from shapely.geometry import LineString

from spatial_tools import evaluate

ROOT = Path(__file__).resolve().parents[1]
INK = "#183247"
MUTED = "#536b7e"
BLUE = "#2563a6"
GREEN = "#16735e"
RED = "#b74242"
AMBER = "#b97718"
PAPER = "#ffffff"
WALL = "#dce3e8"

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 12,
        "text.color": INK,
        "axes.labelcolor": MUTED,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.edgecolor": "#cbd5df",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "svg.fonttype": "none",
        "svg.hashsalt": "spatial-tools-docs-v1",
    }
)


def example(name: str) -> dict:
    return json.loads((ROOT / "examples" / f"{name}.json").read_text())


def checked(request: dict, status: str) -> dict:
    result = evaluate(request)
    if result["status"] != status:
        raise ValueError(f"Figure expects {status}, runtime returned {result['status']}")
    return result["result"]


def canvas(title: str, subtitle: str, height: float = 6):
    fig = plt.figure(figsize=(12, height), facecolor=PAPER)
    fig.text(0.055, 0.94, title, fontsize=23, fontweight="bold", va="top")
    fig.text(0.055, 0.81 if height < 5 else 0.855, subtitle, fontsize=13.5, color=MUTED)
    return fig


def map_axes(fig, bounds, position, *, units="m", ylabel=True):
    ax = fig.add_axes(position)
    ax.set_xlim(bounds[0], bounds[2])
    ax.set_ylim(bounds[1], bounds[3])
    ax.set_aspect("equal")
    ax.set_xlabel(f"x ({units})", fontsize=11)
    if ylabel:
        ax.set_ylabel(f"y ({units})", fontsize=11)
    ax.tick_params(labelsize=10)
    ax.set_axisbelow(True)
    ax.grid(color="#e8edf1", linewidth=0.7)
    return ax


def rectangle(ax, raw, *, face=WALL, edge=MUTED, alpha=1, zorder=2):
    low, high = raw["min"], raw["max"]
    ax.add_patch(
        Rectangle(
            low,
            high[0] - low[0],
            high[1] - low[1],
            facecolor=face,
            edgecolor=edge,
            linewidth=1.6,
            alpha=alpha,
            zorder=zorder,
        )
    )


def workflow():
    fig = canvas(
        "From a spatial question to a checked answer",
        "Use the skill to describe a scene, call the runtime, and read its evidence.",
        4.4,
    )
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    cards = [
        ("1  ASK", "Choose a question", ["Does it fit?", "Does this route clear?"], BLUE),
        (
            "2  SCENE",
            "Supply the geometry",
            ["Coordinates + frame + units", "Footprint + error bound", "Obstacles + time"],
            BLUE,
        ),
        ("3  CHECK", "Run the calculation", ["uv run spatial-tools \\", "run scene.json"], BLUE),
        (
            "4  RESULT",
            "Read the outcome",
            [
                "supported  ·  model answer",
                "blocked  ·  change plan",
                "unknown  ·  need evidence",
                "invalid  ·  fix input",
            ],
            GREEN,
        ),
    ]
    for i, (step, title, lines, color) in enumerate(cards):
        x = 0.045 + i * 0.242
        ax.add_patch(
            FancyBboxPatch(
                (x, 0.29),
                0.215,
                0.43,
                boxstyle="round,pad=0.008,rounding_size=0.018",
                facecolor="#f4f8fb",
                edgecolor="#d8e2ea",
                linewidth=1.2,
            )
        )
        ax.text(x + 0.015, 0.668, step, fontsize=12, fontweight="bold", color=color)
        ax.text(x + 0.015, 0.605, title, fontsize=13.5, fontweight="bold")
        for j, line in enumerate(lines):
            ax.text(
                x + 0.015,
                0.535 - j * 0.055,
                line,
                fontsize=10.6 if i == 2 else 11.2,
                fontfamily="DejaVu Sans Mono" if i == 2 else "DejaVu Sans",
            )
        if i < 3:
            ax.annotate(
                "",
                xy=(x + 0.232, 0.5),
                xytext=(x + 0.219, 0.5),
                arrowprops={"arrowstyle": "->", "color": BLUE, "lw": 1.7},
            )
    ax.annotate(
        "",
        xy=(0.35, 0.21),
        xytext=(0.88, 0.21),
        arrowprops={"arrowstyle": "->", "color": BLUE, "lw": 1.5},
    )
    ax.text(0.615, 0.12, "Refresh a changing scene and check again", ha="center", fontsize=13)
    ax.text(
        0.055,
        0.035,
        "A clear path is supported only in the supplied 2D model.",
        fontsize=11,
        color=MUTED,
    )
    return fig


def clearance():
    requests = [example("narrow-path"), example("clear-path")]
    results = [checked(requests[0], "blocked"), checked(requests[1], "supported")]
    fig = canvas(
        "Check clearance for the whole body",
        "Disk radius 0.25 m + extra margin 0.10 m = required clearance 0.35 m.",
        6.2,
    )
    for i, (request, result) in enumerate(zip(requests, results, strict=True)):
        left = 0.065 + i * 0.49
        color = RED if i == 0 else GREEN
        status = "blocked" if i == 0 else "supported"
        ax = map_axes(fig, (-0.5, -1.5, 6.5, 2.2), [left, 0.28, 0.40, 0.50])
        wall = request["scene"]["objects"][0]["shape"]
        y = request["query"]["path"][0][1]
        radius = request["query"]["radius"]
        required = result["required_clearance"]
        ax.fill_between([0, 6], y - required, y + required, color=color, alpha=0.09, zorder=1)
        rectangle(ax, wall)
        ax.text(3, 0, "wall", fontsize=15, ha="center", va="center", color=MUTED)
        ax.plot([0, 6], [y, y], color=color, linewidth=2.5, zorder=4)
        ax.scatter([0, 6], [y, y], s=28, color=color, zorder=5)
        ax.add_patch(Circle((3, y), radius, facecolor=color, alpha=0.20, zorder=5))
        ax.add_patch(Circle((3, y), radius, fill=False, edgecolor=color, lw=1.8, zorder=6))
        ax.add_patch(
            Circle((3, y), required, fill=False, edgecolor=AMBER, lw=1.7, linestyle="--", zorder=6)
        )
        top = wall["max"][1]
        ax.plot([4.65, 4.65], [top, y], color=INK, linewidth=1.3, zorder=7)
        for cap in (top, y):
            ax.plot([4.52, 4.78], [cap, cap], color=INK, linewidth=1.3, zorder=7)
        measured = result["minimum_obstacle_clearance"]
        ax.text(
            4.88, (top + y) / 2, f"{measured:.2f} m", fontsize=12, va="center", color=INK, zorder=7
        )
        fig.text(
            left,
            0.79,
            f"{status}  ·  centreline y = {y:g} m",
            fontsize=16,
            fontweight="bold",
            color=color,
        )
        sign = "<" if i == 0 else ">"
        fig.text(
            left,
            0.17,
            f"{measured:.2f} m {sign} {required:.2f} m required",
            fontsize=15,
            fontweight="bold",
            color=color,
        )
        fig.text(
            left,
            0.115,
            "Body clips the wall." if i == 0 else "Body and margin clear the wall.",
            fontsize=13,
            color=MUTED,
        )
    fig.text(
        0.055,
        0.04,
        "Dashed ring = disk + margin. Complete synthetic scene; uncertainty 0 m.",
        fontsize=11.5,
        color=MUTED,
    )
    return fig


def rotated_fit():
    from spatial_tools.engine import shape

    requests = [example("unrotated-fit"), example("rotated-fit")]
    results = [checked(requests[0], "blocked"), checked(requests[1], "supported")]
    fig = canvas(
        "Rotation can change whether a panel fits",
        "A 600 × 350 mm panel inside a 400 × 650 mm opening; requested margin 10 mm.",
        6.4,
    )
    for i, (request, result) in enumerate(zip(requests, results, strict=True)):
        left = 0.075 + i * 0.49
        color = RED if i == 0 else GREEN
        ax = map_axes(fig, (-350, -380, 350, 380), [left, 0.23, 0.365, 0.54], units="mm")
        item, container = [obj["shape"] for obj in request["scene"]["objects"]]
        rectangle(ax, container, face="#eef5fc", edge=BLUE, zorder=1)
        rotation = request["query"]["rotation_degrees"]
        polygon = affinity.rotate(shape(item, "diagram item"), rotation, origin="centroid")
        ax.add_patch(
            Polygon(
                list(polygon.exterior.coords),
                facecolor=color,
                edgecolor=color,
                alpha=0.25,
                linewidth=2,
                zorder=2,
            )
        )
        ax.add_patch(
            Polygon(
                list(polygon.exterior.coords), fill=False, edgecolor=color, linewidth=2, zorder=3
            )
        )
        width, height = polygon.bounds[2] - polygon.bounds[0], polygon.bounds[3] - polygon.bounds[1]
        ax.text(
            0,
            0,
            f"panel\n{width:g} × {height:g} mm",
            fontsize=14,
            ha="center",
            va="center",
            color=color,
            zorder=4,
        )
        title = "0° placement  ·  blocked" if i == 0 else "90° placement  ·  supported"
        fig.text(left, 0.79, title, fontsize=16, fontweight="bold", color=color)
        caption = (
            "Too wide at this orientation."
            if i == 0
            else (f"{result['boundary_clearance']:g} mm clearance on every side.")
        )
        fig.text(left, 0.12, caption, fontsize=14, fontweight="bold", color=color)
    fig.text(
        0.055,
        0.04,
        "Static placement only. This does not check an insertion or rotation sweep.",
        fontsize=11.5,
        color=MUTED,
    )
    return fig


def routes():
    original = example("plan-route")
    initial = checked(original, "supported")
    changed = copy.deepcopy(original)
    changed["scene"]["objects"][0]["shape"].update(min=[2, -1.6], max=[4, 1.6])
    changed["scene"]["observed_at"] = "2026-10-10T12:00:02Z"
    changed["query"]["as_of"] = "2026-10-10T12:00:03Z"
    old_route = copy.deepcopy(changed)
    old_route["operation"] = "check_path"
    old_route["query"] = {key: changed["query"][key] for key in ("radius", "margin", "as_of")}
    old_route["query"]["path"] = initial["path"]
    checked(old_route, "blocked")
    refreshed = checked(changed, "supported")
    fig = canvas(
        "Refresh the map before using a route",
        "The same start, goal, and footprint can need a different path when an obstacle changes.",
        5.2,
    )
    panels = [
        (
            original,
            initial["path"],
            GREEN,
            "1  Plan · supported",
            f"{initial['length']:g} m grid route",
        ),
        (changed, initial["path"], RED, "2  Refresh · blocked", "Old route hits the larger wall"),
        (
            changed,
            refreshed["path"],
            GREEN,
            "3  Replan · supported",
            f"{refreshed['length']:g} m grid route",
        ),
    ]
    for i, (request, path, color, title, caption) in enumerate(panels):
        left = 0.065 + i * 0.325
        ax = map_axes(fig, (-1.5, -3.5, 7.5, 3.5), [left, 0.24, 0.275, 0.53], ylabel=i == 0)
        rectangle(ax, request["scene"]["workspace"], face="none", edge="#a8b8c5", zorder=1)
        clearance = request["query"]["radius"] + request["query"]["margin"]
        envelope = LineString(path).buffer(clearance, quad_segs=32)
        ax.add_patch(
            Polygon(
                list(envelope.exterior.coords),
                facecolor=color,
                edgecolor="none",
                alpha=0.14,
                zorder=2,
            )
        )
        rectangle(ax, request["scene"]["objects"][0]["shape"], zorder=3)
        ax.text(3, 0.15, "wall", ha="center", fontsize=12, color=MUTED)
        x, y = zip(*path, strict=True)
        ax.plot(x, y, color=color, linewidth=2.4, zorder=4)
        for label, point in (("S", request["query"]["start"]), ("G", request["query"]["goal"])):
            ax.scatter(*point, s=36, edgecolor=BLUE, facecolor="white", linewidth=1.7, zorder=5)
            ax.text(point[0], point[1] + 0.45, label, ha="center", fontsize=12, color=BLUE)
        ax.set_xticks([0, 2, 4, 6])
        ax.set_yticks([-2, 0, 2])
        fig.text(left, 0.77, title, fontsize=14.5, fontweight="bold", color=color)
        fig.text(left, 0.13, caption, fontsize=12, fontweight="bold", color=color)
    fig.text(
        0.055,
        0.04,
        "0.5 m grid · disk radius 0.25 m · margin 0.10 m · uncertainty 0 m. "
        "Routes checked continuously.",
        fontsize=11,
        color=MUTED,
    )
    return fig


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check SVGs against current examples")
    args = parser.parse_args()
    output = ROOT / "docs/images"
    output.mkdir(parents=True, exist_ok=True)
    descriptions = {
        "workflow": (
            "Four steps: ask a spatial question, supply a scene, run a check, read a result. "
            "Refresh changing scenes."
        ),
        "path-clearance": (
            "A disk needs 0.35 m centreline clearance: a 0.20 m gap blocks it, "
            "a 0.40 m gap supports the path."
        ),
        "rotated-fit": (
            "A 600 by 350 mm panel is too wide for a 400 by 650 mm opening, "
            "but fits at 90 degrees with 25 mm clearance."
        ),
        "route-refresh": (
            "An initial 9 m grid route is blocked by an enlarged wall; "
            "a refreshed 10 m route clears it."
        ),
    }
    renderers = {
        "workflow": workflow,
        "path-clearance": clearance,
        "rotated-fit": rotated_fit,
        "route-refresh": routes,
    }
    stale = []
    for name, render in renderers.items():
        fig = render()
        svg = io.BytesIO()
        fig.savefig(
            svg,
            format="svg",
            metadata={
                "Date": None,
                "Creator": "spatial-tools",
                "Title": name.replace("-", " "),
                "Description": descriptions[name],
            },
        )
        # Keep generated path attributes readable without trailing whitespace.
        content = (
            "\n".join(line.rstrip() for line in svg.getvalue().decode().splitlines()) + "\n"
        ).encode()
        path = output / f"{name}.svg"
        if args.check:
            if not path.exists() or path.read_bytes() != content:
                stale.append(path.name)
        else:
            path.write_bytes(content)
            fig.savefig(
                output / f"{name}.png",
                dpi=160,
                metadata={"Software": "spatial-tools", "Description": descriptions[name]},
            )
        plt.close(fig)
    if stale:
        parser.error(f"Regenerate documentation images: {', '.join(stale)}")
    print("Four diagrams checked." if args.check else "Four diagrams rendered as SVG and PNG.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
