"""E2E-style test for SQOP scene observation without Unreal."""

from __future__ import annotations

from typing import Any, Dict, List

from server.observation.scene_observer import observe_scene


def _fake_scene_syncd(objects: List[Dict[str, Any]]):
    def _call(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if path == "/objects/list":
            return {"success": True, "data": {"objects": objects}}
        return {"success": True, "data": {}}

    return _call


def test_scene_observation_builds_12_cave_shots(monkeypatch):
    objects = [
        {
            "mcp_id": "cave_sdf_main",
            "name": "Cave_SDF_Main",
            "kind": "cave_mesh",
            "tags": ["cave", "procedural_cave", "sdf"],
            "bounds": {"min": [-1400, -300, -160], "max": [1800, 420, 760]},
            "generation": {"resolution": 48, "roughness": 0.74},
        }
    ]
    monkeypatch.setattr("server.scene_tools_common.call_scene_syncd", _fake_scene_syncd(objects))
    observation = observe_scene(scene_id="sqop_test", intent="create a creepy cave")
    assert observation.scene_id == "sqop_test"
    assert len(observation.screenshots) == 12
    assert observation.screenshots[0].shot_id == "entrance_wide"
    assert observation.metrics["main_mesh_exists"] is True
    assert observation.metrics["triangle_count"] >= 30000
