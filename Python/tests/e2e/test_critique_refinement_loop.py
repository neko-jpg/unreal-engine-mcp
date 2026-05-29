"""E2E quality loop test for cave critique and refinement."""

from __future__ import annotations

from typing import Any, Dict, List

import pytest

from server.agents.base_agent import AgentContext
from server.agents.domain_agents.vision_critique_domain_agent import VisionCritiqueDomainAgent
from server.agents.refinement_compiler import RefinementCompiler
from server.scene_cave_tools import scene_cave_generate_or_refine


def _box_cave_objects() -> List[Dict[str, Any]]:
    return [
        {"mcp_id": "Cave_Floor", "name": "Cave_Floor", "kind": "floor", "tags": ["cave", "stone"], "bounds": {"min": [-600, -600, 0], "max": [600, 600, 40]}},
        {"mcp_id": "Cave_Wall_N", "name": "Cave_Wall_N", "kind": "wall", "tags": ["cave"], "bounds": {"min": [-600, 600, 0], "max": [600, 640, 400]}},
        {"mcp_id": "Cave_Wall_S", "name": "Cave_Wall_S", "kind": "wall", "tags": ["cave"], "bounds": {"min": [-600, -640, 0], "max": [600, -600, 400]}},
        {"mcp_id": "Cave_Wall_E", "name": "Cave_Wall_E", "kind": "wall", "tags": ["cave"], "bounds": {"min": [600, -600, 0], "max": [640, 600, 400]}},
        {"mcp_id": "Cave_Wall_W", "name": "Cave_Wall_W", "kind": "wall", "tags": ["cave"], "bounds": {"min": [-640, -600, 0], "max": [-600, 600, 400]}},
        {"mcp_id": "Cave_Ceiling", "name": "Cave_Ceiling", "kind": "ceiling", "tags": ["cave"], "bounds": {"min": [-600, -600, 400], "max": [600, 600, 440]}},
    ]


def _fake_scene_syncd(objects: List[Dict[str, Any]]):
    def _call(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if path == "/objects/list":
            return {"success": True, "data": {"objects": objects}}
        if path == "/objects/bulk-upsert":
            objects.extend(payload.get("objects", []))
            return {"success": True, "data": {"upserted_count": len(payload.get("objects", []))}}
        return {"success": True, "data": {}}

    return _call


@pytest.mark.asyncio
async def test_critique_loop_produces_quality_vector_and_refinement(monkeypatch):
    objects = _box_cave_objects()
    monkeypatch.setattr("server.scene_tools_common.call_scene_syncd", _fake_scene_syncd(objects))
    monkeypatch.setattr("server.scene_cave_tools.scene_create_sdf_mesh", lambda **kwargs: {"success": True})
    monkeypatch.setattr("server.scene_cave_tools.scene_upsert_actors", lambda **kwargs: {"success": True})
    monkeypatch.setattr("server.scene_cave_tools._persist_quality_metrics", lambda payload: "quality.json")
    for module in ("pcg_tools", "lighting_tools", "audio_tools", "niagara_tools", "rendering_tools", "testing_validation_tools", "actor_tools"):
        monkeypatch.setattr(f"server.{module}.get_unreal_connection", lambda: None)

    result = scene_cave_generate_or_refine(scene_id="critique_test", force_geometry=True, resolution=48)
    assert result["success"] is True
    assert "quality_vector" in result
    assert result["final_score"] >= 0.0

    agent = VisionCritiqueDomainAgent({})
    critique = await agent.execute("critique cave quality", AgentContext(scene_id="critique_test"))
    assert critique.success is True
    assert "quality_vector" in critique.data
    assert len(critique.data["observation"]["screenshots"]) == 12
    plan = RefinementCompiler().compile(
        critique.data["quality_vector"],
        type("Obs", (), {"metrics": critique.data["math_scores"], "actors": critique.data["observation"]["actors"]})(),
        critique.data["gate_result"],
        critique.data["vlm_scores"],
    )
    assert isinstance(plan, list)
