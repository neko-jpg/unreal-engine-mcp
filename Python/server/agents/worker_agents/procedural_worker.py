"""Procedural Worker Agent - Handles procedural generation tasks."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from server.agents.base_agent import AgentContext, AgentResult, BaseAgent

logger = logging.getLogger("agents.procedural_worker")


class ProceduralWorkerAgent(BaseAgent):
    """Worker agent for procedural geometry generation.
    
    Capabilities:
    - SDF mesh generation
    - WFC grid generation
    - L-system splines
    - Superformula meshes
    - Procedural mesh upsert
    """

    name = "procedural_worker"
    description = "Handles procedural geometry and mesh generation"
    capabilities = [
        "procedural.sdf_mesh",
        "procedural.wfc_grid",
        "procedural.wfc_semantic",
        "procedural.lsystem_spline",
        "procedural.mesh_upsert",
    ]
    domains = ["procedural", "mesh_editing"]

    async def execute(self, intent: str, context: AgentContext) -> AgentResult:
        """Execute procedural generation tasks."""
        self.logger.info(f"ProceduralWorker executing: {intent[:80]}...")
        text_lower = intent.lower()

        if "sdf" in text_lower or "cave" in text_lower:
            return await self._generate_sdf_cave(context)
        elif "wfc" in text_lower or "wave function" in text_lower:
            return await self._generate_wfc_grid(context)
        elif "lsystem" in text_lower or "spline" in text_lower:
            return await self._generate_lsystem(context)
        elif "superformula" in text_lower:
            return await self._generate_superformula(context)
        else:
            return AgentResult(
                success=False,
                error=f"Unknown procedural task: {intent}",
            )

    async def _generate_sdf_cave(self, context: AgentContext) -> AgentResult:
        """Generate SDF cave mesh."""
        result = await self.call_tool_async(
            "scene_create_cave_sdf",
            scene_id=context.scene_id,
            seed=context.metadata.get("seed", 252539),
            chamber_count=context.metadata.get("chamber_count", 5),
            branch_count=context.metadata.get("branch_count", 3),
            roughness=context.metadata.get("roughness", 0.72),
            domain_warp=context.metadata.get("domain_warp", 0.55),
            resolution=context.metadata.get("resolution", 36),
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "SDF cave generation failed"),
                data={"raw_result": result},
            )

        return AgentResult(
            success=True,
            data={
                "actor_name": result.get("actor_name"),
                "mcp_id": result.get("mcp_id"),
                "sdf_tree": result.get("sdf_tree"),
            },
        )

    async def _generate_wfc_grid(self, context: AgentContext) -> AgentResult:
        """Generate WFC grid."""
        result = await self.call_tool_async(
            "scene_create_wfc_grid",
            width=context.metadata.get("width", 4),
            height=context.metadata.get("height", 4),
            tiles=context.metadata.get("tiles", []),
            constraints=context.metadata.get("constraints", []),
            seed=context.metadata.get("seed"),
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "WFC generation failed"),
                data={"raw_result": result},
            )

        return AgentResult(
            success=True,
            data={"grid": result.get("data", {}).get("tiles", [])},
        )

    async def _generate_lsystem(self, context: AgentContext) -> AgentResult:
        """Generate L-system spline."""
        result = await self.call_tool_async(
            "scene_create_lsystem_spline",
            mcp_id=context.metadata.get("mcp_id", "lsystem_001"),
            preset=context.metadata.get("preset", "Tree3D"),
            iterations=context.metadata.get("iterations", 3),
            step_length=context.metadata.get("step_length", 50),
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "L-system generation failed"),
                data={"raw_result": result},
            )

        return AgentResult(
            success=True,
            data={"spline": result},
        )

    async def _generate_superformula(self, context: AgentContext) -> AgentResult:
        """Generate superformula mesh."""
        result = await self.call_tool_async(
            "scene_create_superformula_mesh",
            mcp_id=context.metadata.get("mcp_id", "superformula_001"),
            resolution=context.metadata.get("resolution", 32),
            scale=context.metadata.get("scale", 100),
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Superformula generation failed"),
                data={"raw_result": result},
            )

        return AgentResult(
            success=True,
            data={"mesh": result},
        )
