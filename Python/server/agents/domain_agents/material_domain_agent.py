"""Material Domain Agent - Expert in material creation and application."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from server.agents.base_agent import AgentContext, AgentResult, BaseAgent

logger = logging.getLogger("agents.material_domain")


class MaterialDomainAgent(BaseAgent):
    """Domain agent for material operations.
    
    Capabilities:
    - Material instance creation
    - Parameter updates
    - Material application to actors
    - Color/roughness/metallic adjustments
    """

    name = "material_domain"
    description = "Expert in material creation and application"
    capabilities = [
        "material.batch_update_parameters",
        "material.create_instance",
        "material.apply_to_actor",
        "material.set_scalar",
        "material.set_vector",
        "material.set_mesh_color",
    ]
    domains = ["material", "rendering"]

    def __init__(self, tool_registry: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(tool_registry)
        # Register worker agents for advanced material coordination
        from server.agents.worker_agents.mesh_worker import MeshWorkerAgent
        from server.agents.worker_agents.pcg_worker import PCGWorkerAgent

        self.register_sub_agent(MeshWorkerAgent(tool_registry))
        self.register_sub_agent(PCGWorkerAgent(tool_registry))

    async def execute(self, intent: str, context: AgentContext) -> AgentResult:
        """Execute material operations."""
        self.logger.info(f"MaterialDomain executing: {intent[:80]}...")
        text_lower = intent.lower()

        if "wet" in text_lower or "water" in text_lower:
            return await self._apply_wet_material(context)
        elif "stone" in text_lower or "rock" in text_lower:
            return await self._apply_stone_material(context)
        elif "color" in text_lower:
            return await self._apply_color_material(context)
        elif "cave" in text_lower or "cavern" in text_lower:
            return await self._apply_cave_material(context)
        else:
            return await self._apply_default_material(context)

    async def _apply_wet_material(self, context: AgentContext) -> AgentResult:
        """Apply wet-looking material with multi-step workflow."""
        actor_name = context.metadata.get("actor_name", "Cave_SDF_Main")
        steps = []

        # Base wet stone color
        result = await self.call_tool_async(
            "set_mesh_material_color",
            blueprint_name=actor_name,
            component_name="ProceduralMeshComponent0",
            color=[0.15, 0.17, 0.2],
        )
        steps.append({"step": "base_color", "result": result})

        # Add specular highlight via material instance parameter
        result = await self.call_tool_async(
            "batch_update_material_parameters",
            instance_path=f"/Game/Materials/MI_{actor_name}",
            parameters=[
                {"name": "Roughness", "type": "scalar", "value": 0.15},
                {"name": "Metallic", "type": "scalar", "value": 0.05},
                {"name": "Specular", "type": "scalar", "value": 0.8},
            ],
        )
        steps.append({"step": "material_params", "result": result})

        failures = [s for s in steps if s["result"].get("success") is False]

        return AgentResult(
            success=len(failures) < len(steps),
            data={"material": "wet_stone", "steps": steps},
            warnings=[f"{s['step']}: {s['result'].get('error')}" for s in failures],
        )

    async def _apply_stone_material(self, context: AgentContext) -> AgentResult:
        """Apply stone material with roughness/metallic tuning."""
        actor_name = context.metadata.get("actor_name", "Cave_SDF_Main")
        steps = []

        result = await self.call_tool_async(
            "set_mesh_material_color",
            blueprint_name=actor_name,
            component_name="ProceduralMeshComponent0",
            color=[0.35, 0.32, 0.28],
        )
        steps.append({"step": "base_color", "result": result})

        result = await self.call_tool_async(
            "batch_update_material_parameters",
            instance_path=f"/Game/Materials/MI_{actor_name}",
            parameters=[
                {"name": "Roughness", "type": "scalar", "value": 0.85},
                {"name": "Metallic", "type": "scalar", "value": 0.0},
            ],
        )
        steps.append({"step": "material_params", "result": result})

        failures = [s for s in steps if s["result"].get("success") is False]

        return AgentResult(
            success=len(failures) < len(steps),
            data={"material": "stone", "steps": steps},
            warnings=[f"{s['step']}: {s['result'].get('error')}" for s in failures],
        )

    async def _apply_color_material(self, context: AgentContext) -> AgentResult:
        """Apply colored material."""
        color = context.metadata.get("color", [1.0, 1.0, 1.0])
        actor_name = context.metadata.get("actor_name", "Cave_SDF_Main")
        
        result = await self.call_tool_async(
            "set_mesh_material_color",
            blueprint_name=actor_name,
            component_name="ProceduralMeshComponent0",
            color=color,
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Color material application failed"),
            )

        return AgentResult(
            success=True,
            data={"material": "colored", "color": color},
        )

    async def _apply_cave_material(self, context: AgentContext) -> AgentResult:
        """Apply multi-layer cave material (wet stone + moss + roughness)."""
        actor_name = context.metadata.get("actor_name", "Cave_SDF_Main")
        steps = []

        # Wet stone base
        result = await self.call_tool_async(
            "set_mesh_material_color",
            blueprint_name=actor_name,
            component_name="ProceduralMeshComponent0",
            color=[0.18, 0.2, 0.22],
        )
        steps.append({"step": "cave_base_color", "result": result})

        # Rough wet parameters
        result = await self.call_tool_async(
            "batch_update_material_parameters",
            instance_path=f"/Game/Materials/MI_{actor_name}",
            parameters=[
                {"name": "Roughness", "type": "scalar", "value": 0.25},
                {"name": "Metallic", "type": "scalar", "value": 0.02},
                {"name": "Specular", "type": "scalar", "value": 0.6},
            ],
        )
        steps.append({"step": "cave_material_params", "result": result})

        # Delegate to mesh worker for UV adjustments if needed
        mesh_result = await self.delegate(
            "mesh_worker",
            f"adjust UVs for cave material on {actor_name}",
            context,
        )
        steps.append({"step": "mesh_uv_adjust", "result": mesh_result.to_dict()})

        failures = [s for s in steps if not s["result"].get("success", True)]

        return AgentResult(
            success=len(failures) < len(steps),
            data={"material": "cave_multi_layer", "steps": steps},
            warnings=[f"{s['step']}: {s['result'].get('error')}" for s in failures],
        )

    async def _apply_default_material(self, context: AgentContext) -> AgentResult:
        """Apply default material."""
        return AgentResult(
            success=True,
            data={"material": "default"},
        )
