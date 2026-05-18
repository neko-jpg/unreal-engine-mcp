"""Unit tests for the four #26 procedural realization MCP wrappers.

These tests validate parameter handling and the Unreal-unavailable failure
path WITHOUT requiring a running editor. They monkeypatch
get_unreal_connection so the wrappers exercise their argument validation
and envelope translation without opening a TCP socket.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

import pytest


# Ensure Python/ is on sys.path so `from server import ...` works regardless
# of the CWD pytest is launched from.
REPO_PYTHON = Path(__file__).resolve().parents[2]
if str(REPO_PYTHON) not in sys.path:
    sys.path.insert(0, str(REPO_PYTHON))


@pytest.fixture
def fake_conn(monkeypatch):
    """Patch get_unreal_connection so wrappers exercise their argument plumbing
    without hitting a real Unreal Editor. Returns a recording stub.
    """
    calls: list[tuple[str, Dict[str, Any]]] = []

    class FakeConn:
        def send_command(self, name: str, params: Dict[str, Any]) -> Dict[str, Any]:
            calls.append((name, params))
            return {"success": True, "data": {"echoed_params": params}}

    fake = FakeConn()

    def _factory():
        return fake

    import server.scene_tools_common as stc
    monkeypatch.setattr(stc, "get_unreal_connection", _factory, raising=True)
    return calls


def test_spawn_procedural_actor_batch_forwards_payload(fake_conn):
    import server.scene_tools as st
    placements = [
        {
            "mcp_id": "p1",
            "actor_class": "StaticMeshActor",
            "static_mesh": "/Engine/BasicShapes/Cube.Cube",
            "location": [0, 0, 0],
            "rotation": [0, 0, 0],
            "scale": [1, 1, 1],
        }
    ]
    out = st.scene_spawn_procedural_actor_batch(
        placements=placements,
        group_id="run_001",
        max_actors=42,
        focus_viewport=True,
    )
    assert out["success"] is True
    assert len(fake_conn) == 1
    name, payload = fake_conn[0]
    assert name == "spawn_procedural_actor_batch"
    assert payload["placements"] == placements
    assert payload["group_id"] == "run_001"
    assert payload["max_actors"] == 42
    assert payload["focus_viewport"] is True


def test_spawn_procedural_actor_batch_rejects_non_list():
    import server.scene_tools as st
    out = st.scene_spawn_procedural_actor_batch(placements="not-a-list")  # type: ignore[arg-type]
    assert out["success"] is False
    assert "placements" in out.get("error", "")


def test_create_spline_mesh_from_segments_forwards_payload(fake_conn):
    import server.scene_tools as st
    segs = [{"start": [0, 0, 0], "end": [100, 0, 0]}]
    out = st.scene_create_spline_mesh_from_segments(
        actor_name="ProcSpline_001",
        segments=segs,
        mesh_path="/Engine/BasicShapes/Cylinder.Cylinder",
        mcp_id="ps1",
        material_path="/Engine/EngineMaterials/DefaultMaterial.DefaultMaterial",
        forward_axis="Y",
        max_segments=999,
        tags=["procedural_lsys"],
    )
    assert out["success"] is True
    assert len(fake_conn) == 1
    name, payload = fake_conn[0]
    assert name == "create_spline_mesh_from_segments"
    assert payload["actor_name"] == "ProcSpline_001"
    assert payload["segments"] == segs
    assert payload["mesh_path"].endswith("Cylinder.Cylinder")
    assert payload["mcp_id"] == "ps1"
    assert payload["material_path"].endswith("DefaultMaterial")
    assert payload["forward_axis"] == "Y"
    assert payload["max_segments"] == 999
    assert payload["tags"] == ["procedural_lsys"]


def test_create_spline_mesh_from_segments_requires_segments():
    import server.scene_tools as st
    out = st.scene_create_spline_mesh_from_segments(
        actor_name="A",
        segments=[],  # empty
        mesh_path="/Engine/BasicShapes/Cube.Cube",
    )
    assert out["success"] is False
    assert "segments" in out.get("error", "")


def test_create_data_layer_for_generation_forwards_payload(fake_conn):
    import server.scene_tools as st
    ids = ["a", "b", "c"]
    out = st.scene_create_data_layer_for_generation(
        data_layer_name="Procedural/WFC_Run_001",
        actor_mcp_ids=ids,
        color_hex="#FF8800",
        initial_state="Loaded",
    )
    assert out["success"] is True
    assert len(fake_conn) == 1
    name, payload = fake_conn[0]
    assert name == "create_data_layer_for_generation"
    assert payload["data_layer_name"] == "Procedural/WFC_Run_001"
    assert payload["actor_mcp_ids"] == ids
    assert payload["color_hex"] == "#FF8800"
    assert payload["initial_state"] == "Loaded"


def test_create_data_layer_for_generation_requires_actor_ids():
    import server.scene_tools as st
    out = st.scene_create_data_layer_for_generation(
        data_layer_name="Layer",
        actor_mcp_ids=[],
    )
    assert out["success"] is False
    assert "actor_mcp_ids" in out.get("error", "")


def test_clear_generated_group_refuses_empty_filter():
    import server.scene_tools as st
    out = st.scene_clear_generated_group()
    assert out["success"] is False
    err = out.get("error", "")
    assert "group_id" in err and "required_tags" in err


def test_clear_generated_group_dry_run_default(fake_conn):
    import server.scene_tools as st
    out = st.scene_clear_generated_group(group_id="run_001")
    assert out["success"] is True
    assert len(fake_conn) == 1
    name, payload = fake_conn[0]
    assert name == "clear_generated_group"
    assert payload["group_id"] == "run_001"
    # Dry-run default must be true (safety guard).
    assert payload["dry_run"] is True
    assert payload["max_delete"] == 10000
    assert "required_tags" not in payload


def test_clear_generated_group_required_tags_only(fake_conn):
    import server.scene_tools as st
    out = st.scene_clear_generated_group(
        required_tags=["procedural_generated"], dry_run=False, max_delete=200
    )
    assert out["success"] is True
    assert len(fake_conn) == 1
    name, payload = fake_conn[0]
    assert name == "clear_generated_group"
    assert payload["required_tags"] == ["procedural_generated"]
    assert payload["dry_run"] is False
    assert payload["max_delete"] == 200
    assert "group_id" not in payload
