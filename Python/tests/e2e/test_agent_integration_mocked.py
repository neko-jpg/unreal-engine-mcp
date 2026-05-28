"""Mocked E2E tests for the enhanced agent system.

These tests verify the enhanced domain agents, coordination logic,
and context propagation without requiring a live UE connection.

Run with: python test_agent_integration_mocked.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock the mcp module to avoid import errors
class MockMCP:
    class FastMCP:
        def __init__(self, *args, **kwargs):
            pass
        def tool(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator

sys.modules['mcp'] = MockMCP()
sys.modules['mcp.server'] = MockMCP()
sys.modules['mcp.server.fastmcp'] = MockMCP()

from server.agents.base_agent import AgentContext, AgentResult
from server.agents.domain_agents.lighting_domain_agent import LightingDomainAgent
from server.agents.domain_agents.material_domain_agent import MaterialDomainAgent
from server.agents.domain_agents.validation_domain_agent import ValidationDomainAgent
from server.agents.domain_agents.architecture_domain_agent import ArchitectureDomainAgent
from server.agents.domain_agents.landscape_domain_agent import LandscapeDomainAgent
from server.agents.domain_agents.foliage_domain_agent import FoliageDomainAgent
from server.agents.master_orchestrator import MasterOrchestrator


def create_mock_registry():
    """Create a mock tool registry that returns success for any call."""
    registry = {}
    async def mock_tool(**kwargs):
        return {"success": True, "data": kwargs}
    registry["set_light_intensity"] = mock_tool
    registry["spawn_actor"] = mock_tool
    registry["set_light_color"] = mock_tool
    registry["set_light_attenuation_radius"] = mock_tool
    registry["set_height_fog_properties"] = mock_tool
    registry["set_mesh_material_color"] = mock_tool
    registry["batch_update_material_parameters"] = mock_tool
    registry["run_collision_validation"] = mock_tool
    registry["run_navigation_validation"] = mock_tool
    registry["run_performance_budget_validation"] = mock_tool
    registry["run_gameplay_screenshot_test"] = mock_tool
    registry["construct_house"] = mock_tool
    registry["create_castle_fortress"] = mock_tool
    registry["create_tower"] = mock_tool
    registry["create_landscape"] = mock_tool
    registry["apply_landscape_material"] = mock_tool
    registry["set_landscape_grass_output"] = mock_tool
    registry["foliage_paint"] = mock_tool
    registry["create_procedural_foliage_spawner"] = mock_tool
    registry["landscape_flatten"] = mock_tool
    return registry


@pytest.mark.asyncio
async def test_lighting_auto_adjust_for_cave():
    """Test LightingDomainAgent auto-adjusts for cave context."""
    print("Testing LightingDomainAgent cave auto-adjust...")
    registry = create_mock_registry()
    agent = LightingDomainAgent(registry)

    context = AgentContext()
    context.metadata["cave_result"] = {
        "success": True,
        "data": {
            "final_metrics": {"depth": 1500, "cave_score": 0.85}
        }
    }

    result = await agent.execute("dark lighting for cave", context)
    assert result.success is True
    assert result.data.get("lighting_setup") == "auto_cave"
    assert "post_generation_steps" not in result.data  # Lighting uses different key
    print("  ✓ Cave auto-adjust works")


@pytest.mark.asyncio
async def test_material_cave_material():
    """Test MaterialDomainAgent cave material workflow."""
    print("Testing MaterialDomainAgent cave material...")
    registry = create_mock_registry()
    agent = MaterialDomainAgent(registry)

    context = AgentContext()
    result = await agent.execute("apply cave material", context)
    assert result.success is True
    assert result.data.get("material") == "cave_multi_layer"
    print("  ✓ Cave material workflow works")


@pytest.mark.asyncio
async def test_validation_full_pipeline():
    """Test ValidationDomainAgent full pipeline with workers."""
    print("Testing ValidationDomainAgent full pipeline...")
    registry = create_mock_registry()
    agent = ValidationDomainAgent(registry)

    # Mock worker agents to avoid actual delegation
    agent.sub_agents["nav_worker"] = MagicMock()
    agent.sub_agents["nav_worker"].execute = AsyncMock(
        return_value=AgentResult(success=True, data={"nav": "ok"})
    )
    agent.sub_agents["validation_worker"] = MagicMock()
    agent.sub_agents["validation_worker"].execute = AsyncMock(
        return_value=AgentResult(success=True, data={"validation": "ok"})
    )

    context = AgentContext()
    result = await agent.execute("run full validation", context)
    assert result.success is True
    assert result.data.get("validation_type") == "full"
    print("  ✓ Full validation pipeline works")


@pytest.mark.asyncio
async def test_architecture_post_construction():
    """Test ArchitectureDomainAgent post-construction coordination."""
    print("Testing ArchitectureDomainAgent post-construction...")
    registry = create_mock_registry()
    agent = ArchitectureDomainAgent(registry)

    # Mock worker agents
    agent.sub_agents["nav_worker"] = MagicMock()
    agent.sub_agents["nav_worker"].execute = AsyncMock(
        return_value=AgentResult(success=True, data={"navmesh": "updated"})
    )
    agent.sub_agents["pcg_worker"] = MagicMock()
    agent.sub_agents["pcg_worker"].execute = AsyncMock(
        return_value=AgentResult(success=True, data={"pcg": "scattered"})
    )
    agent.sub_agents["validation_worker"] = MagicMock()
    agent.sub_agents["validation_worker"].execute = AsyncMock(
        return_value=AgentResult(success=True, data={"validation": "passed"})
    )

    context = AgentContext()
    result = await agent.execute("build castle", context)
    assert result.success is True
    assert "post_construction_steps" in result.data
    print("  ✓ Post-construction coordination works")


@pytest.mark.asyncio
async def test_landscape_post_generation():
    """Test LandscapeDomainAgent post-generation coordination."""
    print("Testing LandscapeDomainAgent post-generation...")
    registry = create_mock_registry()
    agent = LandscapeDomainAgent(registry)

    # Mock worker agents
    agent.sub_agents["procedural_worker"] = MagicMock()
    agent.sub_agents["procedural_worker"].execute = AsyncMock(
        return_value=AgentResult(success=True, data={"procedural": "ok"})
    )
    agent.sub_agents["pcg_worker"] = MagicMock()
    agent.sub_agents["pcg_worker"].execute = AsyncMock(
        return_value=AgentResult(success=True, data={"pcg": "scattered"})
    )
    agent.sub_agents["validation_worker"] = MagicMock()
    agent.sub_agents["validation_worker"].execute = AsyncMock(
        return_value=AgentResult(success=True, data={"validation": "passed"})
    )

    context = AgentContext()
    result = await agent.execute("create landscape", context)
    assert result.success is True
    assert "post_generation_steps" in result.data
    print("  ✓ Post-generation coordination works")


@pytest.mark.asyncio
async def test_master_orchestrator_coordination():
    """Test MasterOrchestrator cross-domain coordination."""
    print("Testing MasterOrchestrator coordination...")
    registry = create_mock_registry()
    orchestrator = MasterOrchestrator(registry)

    # Mock domain agents
    from server.intent.intent_types import Intent
    intent = Intent(raw_text="create cave with lighting", scene_id="main", domains=["cave", "lighting"])
    context = AgentContext()
    results = [
        AgentResult(success=True, data={"cave": "created"}),
        AgentResult(success=True, data={"lighting": "configured"}),
    ]

    coord_result = await orchestrator._coordinate_domains(intent, context, results)
    assert coord_result is not None
    assert "cave_lighting" in coord_result.data.get("coordination_actions", [])
    print("  ✓ Cross-domain coordination works")


@pytest.mark.asyncio
async def test_context_propagation():
    """Test automatic context propagation."""
    print("Testing context propagation...")
    from server.agents.base_agent import BaseAgent

    class ParentAgent(BaseAgent):
        name = "parent"
        async def execute(self, intent, context):
            return AgentResult(success=True)

    class ChildAgent(BaseAgent):
        name = "child"
        async def execute(self, intent, context):
            return AgentResult(success=True, data={"child": "value"})

    parent = ParentAgent({})
    child = ChildAgent({})
    parent.register_sub_agent(child)

    context = AgentContext()
    await parent.delegate("child", "test", context)

    assert "child_result" in context.metadata
    assert context.metadata["child_result"]["data"]["child"] == "value"
    print("  ✓ Context propagation works")


async def main():
    """Run all mocked integration tests."""
    print("=" * 60)
    print("Enhanced Agent System Mocked E2E Tests")
    print("=" * 60)

    try:
        await test_lighting_auto_adjust_for_cave()
        await test_material_cave_material()
        await test_validation_full_pipeline()
        await test_architecture_post_construction()
        await test_landscape_post_generation()
        await test_master_orchestrator_coordination()
        await test_context_propagation()

        print("=" * 60)
        print("All mocked integration tests passed! ✓")
        print("=" * 60)
        return 0

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
