"""Standalone E2E tests for the agent system (no UE/MCP required).

Run with: python3 test_agent_system_standalone.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

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

import pytest

# Now import our code
from server.agents.base_agent import BaseAgent, AgentContext, AgentResult, ToolRegistry
from server.agents.domain_agents import (
    AnimationDomainAgent,
    ArchitectureDomainAgent,
    AssetManagementDomainAgent,
    AudioDomainAgent,
    CaveDomainAgent,
    CinematicDomainAgent,
    FoliageDomainAgent,
    GameplayDomainAgent,
    ImportExportDomainAgent,
    LandscapeDomainAgent,
    LevelManagementDomainAgent,
    LightingDomainAgent,
    MaterialDomainAgent,
    NetworkingDomainAgent,
    NpcDomainAgent,
    PhysicsDomainAgent,
    PostProcessDomainAgent,
    ProjectEditorDomainAgent,
    UiDomainAgent,
    ValidationDomainAgent,
    VfxDomainAgent,
)
from server.agents.master_orchestrator import MasterOrchestrator
from server.agents.worker_agents import (
    MeshWorkerAgent,
    NavWorkerAgent,
    PCGWorkerAgent,
    ProceduralWorkerAgent,
    ValidationWorkerAgent,
)
from server.agents import get_agent_system_status


def test_tool_registry():
    """Test tool registry."""
    print("Testing tool registry...")
    registry = ToolRegistry()
    
    def dummy_tool():
        return {"success": True}
    
    registry.register("dummy", dummy_tool, ["test"])
    assert len(registry.list_all()) == 1
    assert "dummy" in registry.list_all()
    print("  ✓ Tool registry works")


def test_domain_agents():
    """Test all domain agents can be instantiated."""
    print("Testing domain agents...")
    
    agents = [
        CaveDomainAgent,
        ArchitectureDomainAgent,
        LightingDomainAgent,
        MaterialDomainAgent,
        LandscapeDomainAgent,
        FoliageDomainAgent,
        NpcDomainAgent,
        CinematicDomainAgent,
        UiDomainAgent,
        PhysicsDomainAgent,
        AudioDomainAgent,
        VfxDomainAgent,
        AnimationDomainAgent,
        GameplayDomainAgent,
        NetworkingDomainAgent,
        ValidationDomainAgent,
        ImportExportDomainAgent,
        AssetManagementDomainAgent,
        LevelManagementDomainAgent,
        ProjectEditorDomainAgent,
        PostProcessDomainAgent,
    ]
    
    for agent_class in agents:
        agent = agent_class({})
        assert agent is not None
        assert agent.name is not None
        assert len(agent.capabilities) > 0
        print(f"  ✓ {agent.name}")


def test_worker_agents():
    """Test worker agents."""
    print("Testing worker agents...")
    
    workers = [
        ProceduralWorkerAgent,
        PCGWorkerAgent,
        MeshWorkerAgent,
        NavWorkerAgent,
        ValidationWorkerAgent,
    ]
    
    for worker_class in workers:
        worker = worker_class({})
        assert worker is not None
        assert worker.name is not None
        print(f"  ✓ {worker.name}")


def test_orchestrator():
    """Test master orchestrator."""
    print("Testing master orchestrator...")
    
    orchestrator = MasterOrchestrator({})
    assert orchestrator.name == "master_orchestrator"
    assert len(orchestrator.domains) > 0
    assert "cave" in orchestrator._domain_agent_map
    print("  ✓ Master orchestrator works")


def test_intent_resolution():
    """Test intent resolution."""
    print("Testing intent resolution...")
    
    from server.intent.intent_resolver import resolve_intent
    
    # Test cave intent
    resolution = resolve_intent("洞窟を不気味にして")
    assert "cave" in resolution.intent.domains
    print("  ✓ Cave intent resolved")
    
    # Test architecture intent
    resolution = resolve_intent("家を建てて")
    assert "architecture" in resolution.intent.domains
    print("  ✓ Architecture intent resolved")
    
    # Test lighting intent
    resolution = resolve_intent("明るくして")
    assert "lighting" in resolution.intent.domains
    print("  ✓ Lighting intent resolved")


@pytest.mark.asyncio
async def test_async_execution():
    """Test async agent execution."""
    print("Testing async execution...")
    
    class TestAgent(BaseAgent):
        name = "test"
        
        async def execute(self, intent, context):
            return AgentResult(success=True, data={"test": True})
    
    agent = TestAgent({})
    result = await agent.execute("test", AgentContext())
    assert result.success is True
    print("  ✓ Async execution works")


def test_system_status():
    """Test system status."""
    print("Testing system status...")
    
    status = get_agent_system_status()
    assert "initialized" in status
    assert "tool_count" in status
    assert "domain_agent_count" in status
    print(f"  ✓ System status: {status}")


def test_agent_hierarchy():
    """Test agent hierarchy."""
    print("Testing agent hierarchy...")
    
    parent = CaveDomainAgent({})
    child = ProceduralWorkerAgent({})
    parent.register_sub_agent(child)
    
    assert parent.get_sub_agent("procedural_worker") is not None
    print("  ✓ Agent hierarchy works")


def test_capability_registry():
    """Test capability registry."""
    print("Testing capability registry...")
    
    from server.planning.capability_registry import get_default_registry
    
    registry = get_default_registry()
    assert len(registry) > 0
    
    # Check cave capabilities
    cave_caps = registry.list_by_domain("cave")
    assert len(cave_caps) > 0
    print(f"  ✓ Capability registry has {len(registry)} capabilities")
    print(f"    - Cave: {len(cave_caps)} capabilities")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Agent System E2E Tests")
    print("=" * 60)
    
    try:
        test_tool_registry()
        test_domain_agents()
        test_worker_agents()
        test_orchestrator()
        test_intent_resolution()
        asyncio.run(test_async_execution())
        test_system_status()
        test_agent_hierarchy()
        test_capability_registry()
        
        print("=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
        return 0
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
