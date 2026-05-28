"""NPC Domain Agent - Expert in AI characters and navigation."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from server.agents.base_agent import AgentContext, AgentResult, BaseAgent

logger = logging.getLogger("agents.npc_domain")


class NpcDomainAgent(BaseAgent):
    """Domain agent for NPC and AI operations.
    
    Capabilities:
    - AI character spawning
    - Behavior tree setup
    - Patrol route creation
    - NavMesh configuration
    """

    name = "npc_domain"
    description = "Expert in AI characters and navigation"
    capabilities = [
        "ai.spawn_character",
        "ai.setup_behavior",
        "ai.create_patrol",
        "nav.validate",
        "nav.rebuild",
    ]
    domains = ["npc", "ai", "navigation"]

    async def execute(self, intent: str, context: AgentContext) -> AgentResult:
        """Execute NPC operations."""
        self.logger.info(f"NpcDomain executing: {intent[:80]}...")
        text_lower = intent.lower()

        if "spawn" in text_lower or "create" in text_lower:
            return await self._spawn_npc(context)
        elif "behavior" in text_lower or "ai" in text_lower:
            return await self._setup_behavior(context)
        elif "patrol" in text_lower:
            return await self._create_patrol(context)
        elif "navmesh" in text_lower or "nav" in text_lower:
            return await self._setup_navmesh(context)
        else:
            return AgentResult(
                success=False,
                error=f"Unknown NPC task: {intent}",
            )

    async def _spawn_npc(self, context: AgentContext) -> AgentResult:
        """Spawn an NPC character."""
        result = await self.call_tool_async(
            "spawn_actor",
            name="NPC_Character",
            type="Character",
            location=[0, 0, 100],
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "NPC spawn failed"),
            )

        return AgentResult(
            success=True,
            data={"npc": result},
        )

    async def _setup_behavior(self, context: AgentContext) -> AgentResult:
        """Setup AI behavior."""
        result = await self.call_tool_async(
            "scene_set_ai_behavior",
            scene_id=context.scene_id,
            actor_name="NPC_Character",
            behavior_tree="/Game/AI/BT_Default",
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Behavior setup failed"),
            )

        return AgentResult(
            success=True,
            data={"behavior": result},
        )

    async def _create_patrol(self, context: AgentContext) -> AgentResult:
        """Create patrol route."""
        points = context.metadata.get("patrol_points", [
            {"x": -500, "y": 0, "z": 100},
            {"x": 0, "y": 500, "z": 100},
            {"x": 500, "y": 0, "z": 100},
        ])
        
        result = await self.call_tool_async(
            "scene_create_patrol_route",
            scene_id=context.scene_id,
            route_name="PatrolRoute_001",
            points=points,
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Patrol creation failed"),
            )

        return AgentResult(
            success=True,
            data={"patrol": result},
        )

    async def _setup_navmesh(self, context: AgentContext) -> AgentResult:
        """Setup NavMesh."""
        result = await self.call_tool_async(
            "scene_create_navmesh_volume",
            scene_id=context.scene_id,
            volume_name="NavMeshVolume",
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "NavMesh setup failed"),
            )

        return AgentResult(
            success=True,
            data={"navmesh": result},
        )
