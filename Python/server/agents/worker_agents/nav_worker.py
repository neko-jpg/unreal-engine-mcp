"""Navigation Worker Agent - Handles NavMesh and AI navigation tasks."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from server.agents.base_agent import AgentContext, AgentResult, BaseAgent

logger = logging.getLogger("agents.nav_worker")


class NavWorkerAgent(BaseAgent):
    """Worker agent for navigation and AI pathfinding operations.
    
    Capabilities:
    - NavMesh validation
    - NavMesh rebuilding
    - Patrol route creation
    - AI behavior setup
    """

    name = "nav_worker"
    description = "Handles navigation mesh and AI pathfinding"
    capabilities = [
        "nav.validate",
        "nav.rebuild",
        "ai_patrol.upsert",
        "ai_behavior.upsert",
    ]
    domains = ["navigation", "npc", "ai"]

    async def execute(self, intent: str, context: AgentContext) -> AgentResult:
        """Execute navigation tasks."""
        self.logger.info(f"NavWorker executing: {intent[:80]}...")
        text_lower = intent.lower()

        if "validate" in text_lower or "check" in text_lower:
            return await self._validate_navmesh(context)
        elif "rebuild" in text_lower or "build" in text_lower:
            return await self._rebuild_navmesh(context)
        elif "patrol" in text_lower:
            return await self._create_patrol(context)
        elif "behavior" in text_lower or "ai" in text_lower:
            return await self._setup_ai_behavior(context)
        else:
            return AgentResult(
                success=False,
                error=f"Unknown navigation task: {intent}",
            )

    async def _validate_navmesh(self, context: AgentContext) -> AgentResult:
        """Validate NavMesh for the level."""
        result = await self.call_tool_async(
            "run_navigation_validation",
            scope="Level",
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "NavMesh validation failed"),
                data={"raw_result": result},
            )

        return AgentResult(
            success=True,
            data={"validation": result},
        )

    async def _rebuild_navmesh(self, context: AgentContext) -> AgentResult:
        """Rebuild NavMesh."""
        result = await self.call_tool_async(
            "scene_create_navmesh_volume",
            scene_id=context.scene_id,
            volume_name="NavMeshVolume_Cave",
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "NavMesh rebuild failed"),
                data={"raw_result": result},
            )

        return AgentResult(
            success=True,
            data={"navmesh_volume": result},
        )

    async def _create_patrol(self, context: AgentContext) -> AgentResult:
        """Create a patrol route."""
        points = context.metadata.get("patrol_points", [])
        
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
                data={"raw_result": result},
            )

        return AgentResult(
            success=True,
            data={"patrol_route": result},
        )

    async def _setup_ai_behavior(self, context: AgentContext) -> AgentResult:
        """Setup AI behavior for an actor."""
        actor_name = context.metadata.get("actor_name")
        behavior_tree = context.metadata.get("behavior_tree")
        
        if not actor_name:
            return AgentResult(
                success=False,
                error="actor_name required for AI behavior setup",
            )
        
        result = await self.call_tool_async(
            "scene_set_ai_behavior",
            scene_id=context.scene_id,
            actor_name=actor_name,
            behavior_tree=behavior_tree,
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "AI behavior setup failed"),
                data={"raw_result": result},
            )

        return AgentResult(
            success=True,
            data={"ai_behavior": result},
        )
