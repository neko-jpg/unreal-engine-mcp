"""Tests for multi-agent collaboration kernel."""

from __future__ import annotations

from server.agents.base_agent import AgentResult
from server.agents.collaboration import CollaborationKernel


def test_collaboration_kernel_selects_critic_loop_for_quality():
    kernel = CollaborationKernel()
    decision = kernel.decide("critique cave quality", ["quality", "cave"], ["vision_critique_domain", "cave_domain"])
    assert decision.mode == "critic_loop"
    task = kernel.start("critique cave quality", ["quality", "cave"], decision)
    kernel.record_result(task.task_id, "vision_critique_domain", AgentResult(success=True, data={"quality_vector": {"overall": 72.0}}))
    snapshot = kernel.finish(task.task_id, True)
    assert snapshot["task"]["status"] == "complete"
    assert snapshot["evidence"][0]["quality_vector"]["overall"] == 72.0


def test_collaboration_reflection_flags_failures():
    kernel = CollaborationKernel()
    decision = kernel.decide("build cave with lighting material", ["cave", "lighting", "material"], ["cave_domain", "lighting_domain", "material_domain"])
    task = kernel.start("build cave with lighting material", ["cave", "lighting", "material"], decision)
    kernel.record_result(task.task_id, "lighting_domain", AgentResult(success=False, error="tool unavailable"))
    reflection = kernel.reflection(task.task_id)
    assert reflection["needs_retry"] is True
    assert "lighting_domain" in reflection["failed_agents"]
