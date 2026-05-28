"""Landscape Domain Agent - Expert in terrain and landscape operations."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from server.agents.base_agent import AgentContext, AgentResult, BaseAgent

logger = logging.getLogger("agents.landscape_domain")


class LandscapeDomainAgent(BaseAgent):
    """Domain agent for landscape and terrain operations.
    
    Capabilities:
    - Landscape creation
    - Heightmap import/export
    - Sculpting and editing
    - Material application
    - Grass and foliage layers
    """

    name = "landscape_domain"
    description = "Expert in landscape and terrain creation"
    capabilities = [
        "landscape.create",
        "landscape.import_heightmap",
        "landscape.sculpt",
        "landscape.smooth",
        "landscape.apply_material",
        "landscape.add_grass",
    ]
    domains = ["landscape", "terrain", "world_building"]

    def __init__(self, tool_registry: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(tool_registry)
        # Register worker agents for advanced landscape coordination
        from server.agents.worker_agents.procedural_worker import ProceduralWorkerAgent
        from server.agents.worker_agents.pcg_worker import PCGWorkerAgent
        from server.agents.worker_agents.validation_worker import ValidationWorkerAgent

        self.register_sub_agent(ProceduralWorkerAgent(tool_registry))
        self.register_sub_agent(PCGWorkerAgent(tool_registry))
        self.register_sub_agent(ValidationWorkerAgent(tool_registry))

    async def execute(self, intent: str, context: AgentContext) -> AgentResult:
        """Execute landscape operations."""
        self.logger.info(f"LandscapeDomain executing: {intent[:80]}...")
        text_lower = intent.lower()

        if "create" in text_lower or "new" in text_lower:
            return await self._create_landscape(context)
        elif "sculpt" in text_lower:
            return await self._sculpt_landscape(context)
        elif "material" in text_lower:
            return await self._apply_material(context)
        elif "grass" in text_lower or "foliage" in text_lower:
            return await self._add_grass(context)
        else:
            return AgentResult(
                success=False,
                error=f"Unknown landscape task: {intent}",
            )

    async def _create_landscape(self, context: AgentContext) -> AgentResult:
        """Create a new landscape with post-generation coordination."""
        steps = []

        result = await self.call_tool_async(
            "create_landscape",
            actor_name="Landscape",
            quads_per_section=63,
            sections_per_component=1,
        )
        steps.append({"step": "create_landscape", "result": result})

        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Landscape creation failed"),
                data={"steps": steps},
            )

        # Post-generation: apply landscape material
        mat_result = await self.call_tool_async(
            "apply_landscape_material",
            actor_name="Landscape",
            material_path="/Game/Materials/M_Landscape",
        )
        steps.append({"step": "apply_material", "result": mat_result})

        # Post-generation: add grass layer
        grass_result = await self.call_tool_async(
            "set_landscape_grass_output",
            actor_name="Landscape",
            grass_type_path="/Game/Foliage/Grass_Default",
            layer_name="Grass",
        )
        steps.append({"step": "add_grass", "result": grass_result})

        # Post-generation: scatter PCG rocks and details
        pcg_result = await self.delegate(
            "pcg_worker",
            "scatter landscape details (rocks, vegetation)",
            context,
        )
        steps.append({"step": "pcg_details", "result": pcg_result.to_dict()})

        # Post-generation: validate landscape
        val_result = await self.delegate(
            "validation_worker",
            "validate landscape generation",
            context,
        )
        steps.append({"step": "validation", "result": val_result.to_dict()})

        failures = [s for s in steps if not s["result"].get("success", True)]

        return AgentResult(
            success=len(failures) < len(steps),
            data={"landscape": result, "post_generation_steps": steps},
            warnings=[f"{s['step']}: {s['result'].get('error')}" for s in failures],
        )

    async def _sculpt_landscape(self, context: AgentContext) -> AgentResult:
        """Sculpt the landscape."""
        result = await self.call_tool_async(
            "landscape_sculpt",
            actor_name="Landscape",
            brush_radius=200,
            brush_strength=0.5,
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Landscape sculpt failed"),
            )

        return AgentResult(
            success=True,
            data={"sculpt": result},
        )

    async def _apply_material(self, context: AgentContext) -> AgentResult:
        """Apply material to landscape."""
        result = await self.call_tool_async(
            "apply_landscape_material",
            actor_name="Landscape",
            material_path="/Game/Materials/M_Landscape",
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Material application failed"),
            )

        return AgentResult(
            success=True,
            data={"material": result},
        )

    async def _add_grass(self, context: AgentContext) -> AgentResult:
        """Add grass to landscape."""
        result = await self.call_tool_async(
            "set_landscape_grass_output",
            actor_name="Landscape",
            grass_type_path="/Game/Foliage/Grass_Default",
            layer_name="Grass",
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Grass addition failed"),
            )

        return AgentResult(
            success=True,
            data={"grass": result},
        )
