"""Physics Domain Agent - Expert in physics, collision, and destruction."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from server.agents.base_agent import AgentContext, AgentResult, BaseAgent

logger = logging.getLogger("agents.physics_domain")


class PhysicsDomainAgent(BaseAgent):
    """Domain agent for physics and chaos operations.
    
    Capabilities:
    - Physics actor spawning
    - Collision setup
    - Chaos destruction
    - Constraint creation
    """

    name = "physics_domain"
    description = "Expert in physics and destruction"
    capabilities = [
        "physics.spawn_actor",
        "physics.setup_collision",
        "physics.create_constraint",
        "chaos.fracture",
    ]
    domains = ["physics", "chaos", "collision"]

    async def execute(self, intent: str, context: AgentContext) -> AgentResult:
        """Execute physics operations."""
        self.logger.info(f"PhysicsDomain executing: {intent[:80]}...")
        text_lower = intent.lower()

        if "spawn" in text_lower:
            return await self._spawn_physics_actor(context)
        elif "collision" in text_lower:
            return await self._setup_collision(context)
        elif "constraint" in text_lower:
            return await self._create_constraint(context)
        elif "destroy" in text_lower or "fracture" in text_lower:
            return await self._fracture_mesh(context)
        else:
            return AgentResult(
                success=False,
                error=f"Unknown physics task: {intent}",
            )

    async def _spawn_physics_actor(self, context: AgentContext) -> AgentResult:
        """Spawn physics actor."""
        result = await self.call_tool_async(
            "spawn_physics_blueprint_actor",
            name="PhysicsActor",
            location=[0, 0, 200],
            simulate_physics=True,
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Physics actor spawn failed"),
            )

        return AgentResult(
            success=True,
            data={"physics_actor": result},
        )

    async def _setup_collision(self, context: AgentContext) -> AgentResult:
        """Setup collision."""
        result = await self.call_tool_async(
            "set_actor_collision_preset",
            actor_name="PhysicsActor",
            preset="PhysicsActor",
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Collision setup failed"),
            )

        return AgentResult(
            success=True,
            data={"collision": result},
        )

    async def _create_constraint(self, context: AgentContext) -> AgentResult:
        """Create physics constraint."""
        result = await self.call_tool_async(
            "spawn_physics_constraint",
            actor_name="PhysicsConstraint",
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Constraint creation failed"),
            )

        return AgentResult(
            success=True,
            data={"constraint": result},
        )

    async def _fracture_mesh(self, context: AgentContext) -> AgentResult:
        """Fracture mesh using chaos."""
        result = await self.call_tool_async(
            "fracture_geometry_collection",
            asset_path="/Game/Meshes/SM_Rock",
            fracture_type="Uniform",
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Fracture failed"),
            )

        return AgentResult(
            success=True,
            data={"fracture": result},
        )
