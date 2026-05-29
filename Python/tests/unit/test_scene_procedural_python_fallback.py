"""Tests for Python procedural fallbacks when scene-syncd is unavailable."""

from __future__ import annotations

from server.scene_procedural_tools import (
    scene_create_lsystem_spline,
    scene_create_sdf_mesh,
    scene_create_superformula_mesh,
    scene_create_wfc_grid,
)


def _down(path, payload):
    return {"success": False, "error": {"message": "connection refused"}}


def test_sdf_python_fallback(monkeypatch):
    monkeypatch.setattr("server.scene_tools_common.call_scene_syncd", _down)
    res = scene_create_sdf_mesh(mcp_id="py_sdf", sdf_type="sphere", radius=20.0, resolution=8)
    assert res["success"] is True
    assert res["python_fallback"] is True
    assert res["data"]["vertex_count"] > 0


def test_superformula_python_fallback(monkeypatch):
    monkeypatch.setattr("server.scene_tools_common.call_scene_syncd", _down)
    res = scene_create_superformula_mesh(mcp_id="py_sf", resolution=8, scale=10.0)
    assert res["success"] is True
    assert res["python_fallback"] is True
    assert res["data"]["uvs"] is not None


def test_lsystem_python_fallback(monkeypatch):
    monkeypatch.setattr("server.scene_tools_common.call_scene_syncd", _down)
    res = scene_create_lsystem_spline(mcp_id="py_ls", iterations=1)
    assert res["success"] is True
    assert res["python_fallback"] is True
    assert res["data"]["segment_count"] > 0


def test_wfc_python_fallback(monkeypatch):
    monkeypatch.setattr("server.scene_tools_common.call_scene_syncd", _down)
    res = scene_create_wfc_grid(
        width=2,
        height=2,
        tiles=[{"id": "grass", "weight": 1.0}],
        constraints=[
            {"left": "grass", "right": "grass", "direction": "east"},
            {"left": "grass", "right": "grass", "direction": "south"},
        ],
        seed=1,
    )
    assert res["success"] is True
    assert res["python_fallback"] is True
    assert len(res["tiles"]) == 4
