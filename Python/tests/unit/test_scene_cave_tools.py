"""Unit tests for cave orchestration tools."""

from __future__ import annotations

from typing import Any, Dict
from unittest.mock import MagicMock

from server.planning.design_patch import DesignPatch, DirectCommandPatch, Intent
from server.planning.patch_executor import PatchExecutor
from server.scene_cave_tools import (
    scene_cave_audit,
    scene_cave_generate_or_refine,
    scene_create_cave_sdf,
)


def _box_cave_objects():
    return [
        {"mcp_id": "Cave_Floor", "name": "Cave_Floor", "kind": "floor", "tags": ["cave", "stone"], "bounds": {"min": [-600, -600, 0], "max": [600, 600, 40]}},
        {"mcp_id": "Cave_Wall_N", "name": "Cave_Wall_N", "kind": "wall", "tags": ["cave"], "bounds": {"min": [-600, 600, 0], "max": [600, 640, 400]}},
        {"mcp_id": "Cave_Wall_S", "name": "Cave_Wall_S", "kind": "wall", "tags": ["cave"], "bounds": {"min": [-600, -640, 0], "max": [600, -600, 400]}},
        {"mcp_id": "Cave_Wall_E", "name": "Cave_Wall_E", "kind": "wall", "tags": ["cave"], "bounds": {"min": [600, -600, 0], "max": [640, 600, 400]}},
        {"mcp_id": "Cave_Wall_W", "name": "Cave_Wall_W", "kind": "wall", "tags": ["cave"], "bounds": {"min": [-640, -600, 0], "max": [-600, 600, 400]}},
        {"mcp_id": "Cave_Ceiling", "name": "Cave_Ceiling", "kind": "ceiling", "tags": ["cave"], "bounds": {"min": [-600, -600, 400], "max": [600, 600, 440]}},
    ]


def _fake_scene_syncd(objects):
    def _call(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if path == "/objects/list":
            return {"success": True, "data": {"objects": objects}}
        if path == "/objects/bulk-upsert":
            return {"success": True, "data": {"objects": payload.get("objects", [])}}
        if path == "/snapshots/create":
            return {"success": True, "data": {"snapshot_id": "snap"}}
        if path == "/operations/record":
            return {"success": True, "data": {}}
        return {"success": True, "data": {}}

    return _call


def test_cave_audit_detects_box_cave(monkeypatch):
    monkeypatch.setattr("server.scene_tools_common.call_scene_syncd", _fake_scene_syncd(_box_cave_objects()))
    res = scene_cave_audit(scene_id="test")
    assert res["success"] is True
    assert res["cave_metrics"]["is_box_cave"] is True
    assert res["needs_geometry_pass"] is True


def test_create_cave_sdf_sends_capsule_and_domain_warp(monkeypatch):
    captured = {}

    def _mesh(**kwargs):
        captured.update(kwargs)
        return {"success": True, "unreal_response": {"success": True}}

    monkeypatch.setattr("server.scene_cave_tools.scene_create_sdf_mesh", _mesh)
    monkeypatch.setattr("server.scene_cave_tools.scene_upsert_actors", lambda **kwargs: {"success": True, "payload": kwargs})

    res = scene_create_cave_sdf(scene_id="test", chamber_count=4, branch_count=2)
    assert res["success"] is True
    assert captured["sdf_tree"]["type"] == "domain_warp"
    children = captured["sdf_tree"]["child"]["children"]
    assert any(child["type"] == "capsule" for child in children)


def test_cave_generate_or_refine_runs_geometry_for_box_cave(monkeypatch):
    monkeypatch.setattr("server.scene_tools_common.call_scene_syncd", _fake_scene_syncd(_box_cave_objects()))
    monkeypatch.setattr("server.scene_cave_tools.scene_create_sdf_mesh", lambda **kwargs: {"success": True})
    monkeypatch.setattr("server.scene_cave_tools.scene_upsert_actors", lambda **kwargs: {"success": True})
    monkeypatch.setattr("server.pcg_tools.get_unreal_connection", lambda: None)
    monkeypatch.setattr("server.lighting_tools.get_unreal_connection", lambda: None)
    monkeypatch.setattr("server.audio_tools.get_unreal_connection", lambda: None)
    monkeypatch.setattr("server.niagara_tools.get_unreal_connection", lambda: None)
    monkeypatch.setattr("server.rendering_tools.get_unreal_connection", lambda: None)
    monkeypatch.setattr("server.testing_validation_tools.get_unreal_connection", lambda: None)

    res = scene_cave_generate_or_refine(scene_id="test")
    assert res["success"] is True
    assert any(step.get("step") == "scene_create_cave_sdf" for step in res["steps"])


def test_patch_executor_dispatches_python_tool_direct_command(monkeypatch):
    monkeypatch.setattr("server.scene_tools_common.call_scene_syncd", _fake_scene_syncd(_box_cave_objects()))
    patch = DesignPatch(
        patch_id="patch_test",
        scene_id="test",
        intent=Intent(raw_text="audit cave", scene_id="test", domains=["cave"]),
        direct_commands=[
            DirectCommandPatch(
                capability_id="cave.audit",
                command="scene_cave_audit",
                params={"scene_id": "test"},
            )
        ],
    )
    executor = PatchExecutor(unreal_connection=MagicMock())
    report = executor.apply(patch, create_snapshot=False)
    assert report.failed == 0
    assert report.succeeded == 1
    assert report.operations[0].command == "scene_cave_audit"
