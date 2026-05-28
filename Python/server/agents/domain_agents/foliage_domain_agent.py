"""Foliage Domain Agent - Expert in vegetation and foliage."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from server.agents.base_agent import AgentContext, AgentResult, BaseAgent

logger = logging.getLogger("agents.foliage_domain")


class FoliageDomainAgent(BaseAgent):
    """Domain agent for foliage and vegetation operations.
    
    Capabilities:
    - Foliage type creation
    - Static mesh foliage registration
    - Foliage painting
    - Procedural foliage spawning
    """

    name = "foliage_domain"
    description = "Expert in vegetation and foliage"
    capabilities = [
        "foliage.create_type",
        "foliage.register_mesh",
        "foliage.paint",
        "foliage.procedural_spawn",
    ]
    domains = ["foliage", "vegetation", "plants"]

    def __init__(self, tool_registry: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(tool_registry)
        # Register worker agents for advanced foliage coordination
        from server.agents.worker_agents.pcg_worker import PCGWorkerAgent
        from server.agents.worker_agents.validation_worker import ValidationWorkerAgent

        self.register_sub_agent(PCGWorkerAgent(tool_registry))
        self.register_sub_agent(ValidationWorkerAgent(tool_registry))

    async def execute(self, intent: str, context: AgentContext) -> AgentResult:
        """Execute foliage operations."""
        self.logger.info(f"FoliageDomain executing: {intent[:80]}...")
        text_lower = intent.lower()

        if "paint" in text_lower:
            return await self._paint_foliage(context)
        elif "procedural" in text_lower or "spawn" in text_lower:
            return await self._procedural_spawn(context)
        elif "type" in text_lower or "create" in text_lower:
            return await self._create_foliage_type(context)
        else:
            return AgentResult(
                success=False,
                error=f"Unknown foliage task: {intent}",
            )

    async def _paint_foliage(self, context: AgentContext) -> AgentResult:
        """Paint foliage."""
        result = await self.call_tool_async(
            "foliage_paint",
            foliage_type_path="/Game/Foliage/Grass_Default",
            location_xyz=[0, 0, 0],
            radius=500,
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Foliage paint failed"),
            )

        return AgentResult(
            success=True,
            data={"foliage": result},
        )

    async def _procedural_spawn(self, context: AgentContext) -> AgentResult:
        """Procedurally spawn foliage with validation."""
        steps = []

        result = await self.call_tool_async(
            "create_procedural_foliage_spawner",
            asset_name="PFS_Grass",
            asset_path="/Game/Foliage",
        )
        steps.append({"step": "create_spawner", "result": result})

        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Procedural spawn failed"),
                data={"steps": steps},
            )

        # Post-spawn: configure PCG rules for density
        pcg_result = await self.delegate(
            "pcg_worker",
            "configure foliage density and distribution rules",
            context,
        )
        steps.append({"step": "pcg_config", "result": pcg_result.to_dict()})

        # Post-spawn: validate foliage placement
        val_result = await self.delegate(
            "validation_worker",
            "validate foliage placement and density",
            context,
        )
        steps.append({"step": "validation", "result": val_result.to_dict()})

        failures = [s for s in steps if not s["result"].get("success", True)]

        return AgentResult(
            success=len(failures) < len(steps),
            data={"procedural": result, "post_spawn_steps": steps},
            warnings=[f"{s['step']}: {s['result'].get('error')}" for s in failures],
        )

    async def _create_foliage_type(self, context: AgentContext) -> AgentResult:
        """Create foliage type."""
        result = await self.call_tool_async(
            "create_foliage_type",
            asset_name="FT_Grass",
            asset_path="/Game/Foliage",
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Foliage type creation failed"),
            )

        return AgentResult(
            success=True,
            data={"foliage_type": result},
        )
