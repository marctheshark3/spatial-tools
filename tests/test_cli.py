from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def call(*arguments, stdin=None):
    return subprocess.run(
        [sys.executable, "-m", "spatial_tools.cli", *arguments],
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize(
    ("name", "code", "status"),
    [
        ("clear-path", 0, "supported"),
        ("blocked-path", 2, "blocked"),
        ("unknown-scene", 3, "unknown"),
    ],
)
def test_cli_preserves_result_status_and_exit_code(name, code, status):
    result = call("run", str(ROOT / f"examples/{name}.json"))
    assert result.returncode == code
    assert json.loads(result.stdout)["status"] == status
    assert result.stderr == ""


@pytest.mark.parametrize(
    "source",
    [
        '{"schema_version":1,"schema_version":1}',
        '{"radius":NaN}',
        "{",
        "[]",
    ],
)
def test_invalid_json_is_a_structured_rejection(source):
    result = call("run", "-", stdin=source)
    assert result.returncode == 64
    assert json.loads(result.stdout)["status"] == "invalid"


def test_batch_keeps_blocked_and_unknown_outcomes_distinct():
    requests = [
        json.loads((ROOT / f"examples/{name}.json").read_text())
        for name in ("clear-path", "blocked-path", "unknown-scene")
    ]
    result = call("batch", "-", stdin=json.dumps(requests))
    assert result.returncode == 0
    assert [r["status"] for r in json.loads(result.stdout)["results"]] == [
        "supported",
        "blocked",
        "unknown",
    ]


def test_skill_launcher_reaches_the_real_runtime():
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "skills/spatial-reasoning/scripts/spatial.py"),
            "run",
            str(ROOT / "examples/clear-path.json"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert json.loads(result.stdout)["result"]["clear"] is True


def test_installer_is_idempotent_and_preserves_existing_skills(tmp_path):
    command = [sys.executable, str(ROOT / "scripts/install_skill.py"), "--target", str(tmp_path)]
    first = subprocess.run(command, capture_output=True, text=True, check=False)
    assert first.returncode == 0
    target = tmp_path / "spatial-reasoning"
    assert target.is_symlink()
    second = subprocess.run(command, capture_output=True, text=True, check=False)
    assert second.returncode == 0
    target.unlink()
    target.mkdir()
    sentinel = target / "keep.txt"
    sentinel.write_text("user content")
    conflict = subprocess.run(command, capture_output=True, text=True, check=False)
    assert conflict.returncode != 0
    assert sentinel.read_text() == "user content"


def test_detached_skill_prints_setup_instead_of_attempting_an_install(tmp_path):
    # Copy only the launcher: it has neither a repository venv nor a PATH runtime.
    launcher = tmp_path / "skills/spatial-reasoning/scripts/spatial.py"
    launcher.parent.mkdir(parents=True)
    launcher.write_bytes((ROOT / "skills/spatial-reasoning/scripts/spatial.py").read_bytes())
    result = subprocess.run(
        [sys.executable, str(launcher), "--version"],
        env={**os.environ, "PATH": str(tmp_path)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 64
    assert "runtime is missing" in result.stderr
    assert result.stdout == ""
