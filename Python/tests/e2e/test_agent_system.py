"""E2E tests for the agent system.

These tests verify that:
1. All domain agents can be instantiated
2. The tool registry correctly binds available tools
3. The master orchestrator can route intents to appropriate agents
4. Agent execution chains work correctly

Note: These tests do not require a live UE connection.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


class TestAgentSystemInitialization:
    """Test agent system setup and initialization."""

    def test_tool_registry_creation(self):
        """Test that tool registry can be created."""
        from server.agents.base_agent import ToolRegistry
        
        registry = ToolRegistry()
        assert registry is not None
        assert len(registry.list_all()) == 0

    def test_tool_registration(self):
        """Test that tools can be registered."""
        from server.agents.base_agent import ToolRegistry
        
        registry = ToolRegistry()
        
        def dummy_tool():
            return {"success": True}
        
        registry.register("dummy", dummy_tool, ["test"])
        assert len(registry.list_all()) == 1
        assert "dummy" in registry.list_all()
        assert "dummy" in registry.list_by_domain("test")

    def test_base_agent_creation(self):
        """Test that base agents can be created."""
        from server.agents.base_agent import BaseAgent, AgentContext
        
        class TestAgent(BaseAgent):
            name = "test_agent"
            
            async def execute(self, intent, context):
                return {"success": True}
        
        agent = TestAgent()
        assert agent.name == "test_agent"


class TestDomainAgents:
    """Test domain agent instantiation."""

    def test_cave_domain_agent(self):
        """Test CaveDomainAgent can be instantiated."""
        from server.agents.domain_agents.cave_domain_agent import CaveDomainAgent
        
        agent = CaveDomainAgent({})
        assert agent.name == "cave_domain"
        assert "cave.audit" in agent.capabilities

    def test_architecture_domain_agent(self):
        """Test ArchitectureDomainAgent can be instantiated."""
        from server.agents.domain_agents.architecture_domain_agent import ArchitectureDomainAgent
        
        agent = ArchitectureDomainAgent({})
        assert agent.name == "architecture_domain"

    def test_lighting_domain_agent(self):
        """Test LightingDomainAgent can be instantiated."""
        from server.agents.domain_agents.lighting_domain_agent import LightingDomainAgent
        
        agent = LightingDomainAgent({})
        assert agent.name == "lighting_domain"

    def test_all_domain_agents(self):
        """Test all domain agents can be instantiated."""
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
        
        agents = [
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
        ]
        
        for agent_class in agents:
            agent = agent_class({})
            assert agent is not None
            assert agent.name is not None
            assert len(agent.capabilities) > 0


class TestMasterOrchestrator:
    """Test master orchestrator functionality."""

    def test_orchestrator_creation(self):
        """Test orchestrator can be created."""
        from server.agents.master_orchestrator import MasterOrchestrator
        
        orchestrator = MasterOrchestrator({})
        assert orchestrator.name == "master_orchestrator"
        assert len(orchestrator.domains) > 0

    def test_domain_agent_map(self):
        """Test domain to agent mapping."""
        from server.agents.master_orchestrator import MasterOrchestrator
        
        orchestrator = MasterOrchestrator({})
        assert "cave" in orchestrator._domain_agent_map
        assert "lighting" in orchestrator._domain_agent_map
        assert "architecture" in orchestrator._domain_agent_map

    def test_intent_resolution(self):
        """Test intent resolution for cave intents."""
        from server.agents.master_orchestrator import MasterOrchestrator
        from server.intent.intent_resolver import resolve_intent
        
        orchestrator = MasterOrchestrator({})
        
        # Test cave intent
        resolution = resolve_intent("洞窟を不気味にして")
        assert "cave" in resolution.intent.domains
        
        # Test architecture intent
        resolution = resolve_intent("家を建てて")
        assert "architecture" in resolution.intent.domains


class TestWorkerAgents:
    """Test worker agent instantiation."""

    def test_procedural_worker(self):
        """Test ProceduralWorkerAgent."""
        from server.agents.worker_agents.procedural_worker import ProceduralWorkerAgent
        
        agent = ProceduralWorkerAgent({})
        assert agent.name == "procedural_worker"

    def test_pcg_worker(self):
        """Test PCGWorkerAgent."""
        from server.agents.worker_agents.pcg_worker import PCGWorkerAgent
        
        agent = PCGWorkerAgent({})
        assert agent.name == "pcg_worker"

    def test_mesh_worker(self):
        """Test MeshWorkerAgent."""
        from server.agents.worker_agents.mesh_worker import MeshWorkerAgent
        
        agent = MeshWorkerAgent({})
        assert agent.name == "mesh_worker"

    def test_nav_worker(self):
        """Test NavWorkerAgent."""
        from server.agents.worker_agents.nav_worker import NavWorkerAgent
        
        agent = NavWorkerAgent({})
        assert agent.name == "nav_worker"

    def test_validation_worker(self):
        """Test ValidationWorkerAgent."""
        from server.agents.worker_agents.validation_worker import ValidationWorkerAgent
        
        agent = ValidationWorkerAgent({})
        assert agent.name == "validation_worker"


class TestToolBinding:
    """Test that tools can be bound to the registry."""

    def test_cave_tools_exist(self):
        """Test that cave tool modules exist."""
        from server.scene_cave_tools import (
            scene_cave_audit,
            scene_create_cave_sdf,
            scene_validate_cave,
            scene_cave_generate_or_refine,
        )
        
        assert callable(scene_cave_audit)
        assert callable(scene_create_cave_sdf)
        assert callable(scene_validate_cave)
        assert callable(scene_cave_generate_or_refine)

    def test_procedural_tools_exist(self):
        """Test that procedural tool modules exist."""
        from server.scene_procedural_tools import (
            scene_create_sdf_mesh,
            scene_create_wfc_grid,
        )
        
        assert callable(scene_create_sdf_mesh)
        assert callable(scene_create_wfc_grid)

    def test_validation_tools_exist(self):
        """Test that validation tool modules exist."""
        from server.testing_validation_tools import (
            run_collision_validation,
            run_navigation_validation,
        )
        
        assert callable(run_collision_validation)
        assert callable(run_navigation_validation)


class TestIntegration:
    """Integration tests for the full agent system."""

    @pytest.mark.asyncio
    async def test_agent_execution_chain(self):
        """Test that agent execution chain works."""
        from server.agents.base_agent import BaseAgent, AgentContext, AgentResult
        
        class ParentAgent(BaseAgent):
            name = "parent"
            
            async def execute(self, intent, context):
                return AgentResult(success=True, data={"parent": True})
        
        class ChildAgent(BaseAgent):
            name = "child"
            
            async def execute(self, intent, context):
                return AgentResult(success=True, data={"child": True})
        
        parent = ParentAgent({})
        child = ChildAgent({})
        parent.register_sub_agent(child)
        
        result = await parent.delegate("child", "test", AgentContext())
        assert result.success is True
        assert result.data.get("child") is True

    def test_agent_system_status(self):
        """Test agent system status reporting."""
        from server.agents import get_agent_system_status
        
        status = get_agent_system_status()
        assert "initialized" in status
        assert "tool_count" in status
        assert "domain_agent_count" in status


class TestCoordinateDomains:
    """Test cross-domain coordination."""

    @pytest.mark.asyncio
    async def test_cave_lighting_coordination(self):
        """Test cave + lighting coordination."""
        from server.agents.master_orchestrator import MasterOrchestrator
        from server.intent.intent_types import Intent
        from server.agents.base_agent import AgentContext, AgentResult

        orchestrator = MasterOrchestrator({})
        intent = Intent(raw_text="create cave with dark lighting", scene_id="main", domains=["cave", "lighting"])
        context = AgentContext()
        results = [
            AgentResult(success=True, data={"cave": "created"}),
            AgentResult(success=True, data={"lighting": "configured"}),
        ]

        coord_result = await orchestrator._coordinate_domains(intent, context, results)
        assert coord_result is not None
        assert "cave_lighting" in coord_result.data.get("coordination_actions", [])

    @pytest.mark.asyncio
    async def test_architecture_landscape_coordination(self):
        """Test architecture + landscape coordination."""
        from server.agents.master_orchestrator import MasterOrchestrator
        from server.intent.intent_types import Intent
        from server.agents.base_agent import AgentContext, AgentResult

        orchestrator = MasterOrchestrator({})
        intent = Intent(raw_text="build castle on terrain", scene_id="main", domains=["architecture", "landscape"])
        context = AgentContext()
        results = [
            AgentResult(success=True, data={"castle": "built"}),
            AgentResult(success=True, data={"landscape": "created"}),
        ]

        coord_result = await orchestrator._coordinate_domains(intent, context, results)
        assert coord_result is not None
        assert "architecture_landscape" in coord_result.data.get("coordination_actions", [])

    @pytest.mark.asyncio
    async def test_no_coordination_needed(self):
        """Test when no coordination is needed."""
        from server.agents.master_orchestrator import MasterOrchestrator
        from server.intent.intent_types import Intent
        from server.agents.base_agent import AgentContext, AgentResult

        orchestrator = MasterOrchestrator({})
        intent = Intent(raw_text="just lighting", scene_id="main", domains=["lighting"])
        context = AgentContext()
        results = [AgentResult(success=True, data={"lighting": "done"})]

        coord_result = await orchestrator._coordinate_domains(intent, context, results)
        assert coord_result is None


class TestContextPropagation:
    """Test automatic context propagation between agents."""

    @pytest.mark.asyncio
    async def test_delegate_propagates_result(self):
        """Test that delegate() auto-saves result to context metadata."""
        from server.agents.base_agent import BaseAgent, AgentContext, AgentResult

        class ParentAgent(BaseAgent):
            name = "parent"

            async def execute(self, intent, context):
                return AgentResult(success=True)

        class ChildAgent(BaseAgent):
            name = "child"

            async def execute(self, intent, context):
                return AgentResult(success=True, data={"child_key": "child_value"})

        parent = ParentAgent({})
        child = ChildAgent({})
        parent.register_sub_agent(child)

        context = AgentContext()
        result = await parent.delegate("child", "test", context)

        assert result.success is True
        assert "child_result" in context.metadata
        assert context.metadata["child_result"]["data"]["child_key"] == "child_value"
        assert "last_delegate_result" in context.metadata


class TestEnhancedDomainAgents:
    """Test enhanced domain agents with worker coordination."""

    def test_lighting_domain_has_workers(self):
        """Test LightingDomainAgent registers workers."""
        from server.agents.domain_agents.lighting_domain_agent import LightingDomainAgent

        agent = LightingDomainAgent({})
        assert agent.get_sub_agent("procedural_worker") is not None
        assert agent.get_sub_agent("pcg_worker") is not None

    def test_material_domain_has_workers(self):
        """Test MaterialDomainAgent registers workers."""
        from server.agents.domain_agents.material_domain_agent import MaterialDomainAgent

        agent = MaterialDomainAgent({})
        assert agent.get_sub_agent("mesh_worker") is not None
        assert agent.get_sub_agent("pcg_worker") is not None

    def test_validation_domain_has_workers(self):
        """Test ValidationDomainAgent registers workers."""
        from server.agents.domain_agents.validation_domain_agent import ValidationDomainAgent

        agent = ValidationDomainAgent({})
        assert agent.get_sub_agent("nav_worker") is not None
        assert agent.get_sub_agent("validation_worker") is not None

    def test_architecture_domain_has_workers(self):
        """Test ArchitectureDomainAgent registers workers."""
        from server.agents.domain_agents.architecture_domain_agent import ArchitectureDomainAgent

        agent = ArchitectureDomainAgent({})
        assert agent.get_sub_agent("nav_worker") is not None
        assert agent.get_sub_agent("pcg_worker") is not None
        assert agent.get_sub_agent("validation_worker") is not None

    def test_landscape_domain_has_workers(self):
        """Test LandscapeDomainAgent registers workers."""
        from server.agents.domain_agents.landscape_domain_agent import LandscapeDomainAgent

        agent = LandscapeDomainAgent({})
        assert agent.get_sub_agent("procedural_worker") is not None
        assert agent.get_sub_agent("pcg_worker") is not None
        assert agent.get_sub_agent("validation_worker") is not None

    def test_foliage_domain_has_workers(self):
        """Test FoliageDomainAgent registers workers."""
        from server.agents.domain_agents.foliage_domain_agent import FoliageDomainAgent

        agent = FoliageDomainAgent({})
        assert agent.get_sub_agent("pcg_worker") is not None
        assert agent.get_sub_agent("validation_worker") is not None


class TestSceneEditAgentMode:
    """Test scene_edit agent mode integration."""

    def test_scene_edit_agent_mode_exists(self):
        """Test that scene_edit supports agent mode."""
        from server.dialog_tools import scene_edit

        # Just verify the function signature accepts mode="agent"
        import inspect
        sig = inspect.signature(scene_edit)
        params = list(sig.parameters.keys())
        assert "intent" in params
        assert "mode" in params


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
