"""PCG Worker Agent - Handles PCG graph execution and configuration."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from server.agents.base_agent import AgentContext, AgentResult, BaseAgent

logger = logging.getLogger("agents.pcg_worker")


class PCGWorkerAgent(BaseAgent):
    """Worker agent for PCG (Procedural Content Generation) operations.
    
    Capabilities:
    - PCG graph creation and execution
    - Surface sampling
    - Static mesh spawning
    - Spline sampling
    """

    name = "pcg_worker"
    description = "Handles PCG graph operations and content scattering"
    capabilities = [
        "pcg.execute_graph",
        "pcg.create_graph",
        "pcg.add_component",
        "pcg.configure_surface_sampler",
        "pcg.configure_static_mesh_spawner",
    ]
    domains = ["pcg", "procedural"]

    async def execute(self, intent: str, context: AgentContext) -> AgentResult:
        """Execute PCG tasks."""
        self.logger.info(f"PCGWorker executing: {intent[:80]}...")
        text_lower = intent.lower()

        if "scatter" in text_lower or "detail" in text_lower:
            return await self._scatter_details(context)
        elif "execute" in text_lower or "run" in text_lower:
            return await self._execute_graph(context)
        elif "create" in text_lower or "new" in text_lower:
            return await self._create_graph(context)
        else:
            return AgentResult(
                success=False,
                error=f"Unknown PCG task: {intent}",
            )

    async def _scatter_details(self, context: AgentContext) -> AgentResult:
        """Scatter details using PCG on a surface."""
        actor_name = context.metadata.get("actor_name", "Cave_SDF_Main")
        graph_path = context.metadata.get("graph_path", "/Game/PCG/PCGG_CaveWet")
        mesh_path = context.metadata.get("mesh_path", "/Engine/BasicShapes/Cone.Cone")
        density = context.metadata.get("density", 0.45)
        refinement_plan = context.metadata.get("refinement_plan", [])
        distribution_fields = self._build_cave_distribution_fields(density, refinement_plan)

        steps = []
        
        # Create graph
        result = await self.call_tool_async(
            "create_pcg_graph",
            asset_path="/".join(graph_path.split("/")[:-1]) or "/Game/PCG",
            asset_name=graph_path.rsplit("/", 1)[-1] or "PCGG_CaveWet",
        )
        steps.append({"step": "create_graph", "result": result})

        # Configure surface sampler
        result = await self.call_tool_async(
            "configure_pcg_surface_sampler",
            graph_path=graph_path,
            surface_actor=actor_name,
            density=density,
        )
        steps.append({"step": "configure_surface_sampler", "result": result})

        # Configure mesh spawner
        result = await self.call_tool_async(
            "configure_pcg_static_mesh_spawner",
            graph_path=graph_path,
            mesh_path=mesh_path,
        )
        steps.append({"step": "configure_mesh_spawner", "result": result})

        # Add PCG component
        result = await self.call_tool_async(
            "add_pcg_component",
            actor_name=actor_name,
            graph_path=graph_path,
        )
        steps.append({"step": "add_pcg_component", "result": result})

        # Execute graph
        result = await self.call_tool_async(
            "execute_pcg_graph",
            actor_name=actor_name,
        )
        steps.append({"step": "execute_graph", "result": result})

        failures = [s for s in steps if s["result"].get("success") is False]
        
        return AgentResult(
            success=len(failures) == 0,
            data={
                "steps": steps,
                "distribution_fields": distribution_fields,
                "pcg_strategy": "non_uniform_poisson_process",
            },
            warnings=[f"{s['step']}: {s['result'].get('error')}" for s in failures],
        )

    def _build_cave_distribution_fields(self, base_density: float, refinement_plan: Any) -> Dict[str, Any]:
        """Describe cave detail probability fields for downstream PCG tooling."""
        stalactite_boost = 0.0
        if isinstance(refinement_plan, list):
            for item in refinement_plan:
                if not isinstance(item, dict):
                    continue
                for action in item.get("actions", []):
                    if isinstance(action, dict) and action.get("operation") == "spawn_ceiling_stalactites":
                        stalactite_boost += 0.45
        return {
            "lambda_ceiling": {
                "base_density": round(float(base_density) + stalactite_boost, 3),
                "terms": {
                    "ceiling_score": 1.0,
                    "moisture": 0.35,
                    "positive_curvature": 0.45,
                    "player_path_penalty": -0.55,
                },
            },
            "lambda_floor": {
                "base_density": round(float(base_density) * 0.8, 3),
                "terms": {
                    "floor_score": 1.0,
                    "wall_proximity": 0.40,
                    "slope_instability": 0.30,
                },
            },
            "lambda_moss": {
                "base_density": round(float(base_density) * 0.35, 3),
                "terms": {
                    "moisture": 0.70,
                    "low_light": 0.50,
                    "lower_wall_region": 0.35,
                },
            },
        }

    async def _execute_graph(self, context: AgentContext) -> AgentResult:
        """Execute an existing PCG graph."""
        actor_name = context.metadata.get("actor_name", "Cave_SDF_Main")
        
        result = await self.call_tool_async(
            "execute_pcg_graph",
            actor_name=actor_name,
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "PCG execution failed"),
                data={"raw_result": result},
            )

        return AgentResult(
            success=True,
            data={"execution": result},
        )

    async def _create_graph(self, context: AgentContext) -> AgentResult:
        """Create a new PCG graph."""
        asset_path = context.metadata.get("asset_path", "/Game/PCG")
        asset_name = context.metadata.get("asset_name", "PCGG_New")
        
        result = await self.call_tool_async(
            "create_pcg_graph",
            asset_path=asset_path,
            asset_name=asset_name,
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "PCG graph creation failed"),
                data={"raw_result": result},
            )

        return AgentResult(
            success=True,
            data={"graph_path": f"{asset_path}/{asset_name}"},
        )
