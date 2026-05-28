"""Mesh Worker Agent - Handles mesh editing and optimization tasks."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from server.agents.base_agent import AgentContext, AgentResult, BaseAgent

logger = logging.getLogger("agents.mesh_worker")


class MeshWorkerAgent(BaseAgent):
    """Worker agent for mesh editing operations.
    
    Capabilities:
    - Collision generation
    - Nanite enablement
    - UV unwrap
    - Voxel remesh
    - Mesh baking
    """

    name = "mesh_worker"
    description = "Handles static mesh editing and optimization"
    capabilities = [
        "mesh.voxel_remesh",
        "mesh.collision_generate",
        "mesh.nanite_enable",
        "mesh.uv_unwrap",
    ]
    domains = ["mesh_editing", "procedural"]

    async def execute(self, intent: str, context: AgentContext) -> AgentResult:
        """Execute mesh editing tasks."""
        self.logger.info(f"MeshWorker executing: {intent[:80]}...")
        text_lower = intent.lower()

        if "collision" in text_lower:
            return await self._generate_collision(context)
        elif "nanite" in text_lower:
            return await self._enable_nanite(context)
        elif "uv" in text_lower or "unwrap" in text_lower:
            return await self._unwrap_uv(context)
        elif "remesh" in text_lower or "voxel" in text_lower:
            return await self._voxel_remesh(context)
        else:
            return AgentResult(
                success=False,
                error=f"Unknown mesh task: {intent}",
            )

    async def _generate_collision(self, context: AgentContext) -> AgentResult:
        """Generate collision for a mesh actor."""
        actor_name = context.metadata.get("actor_name", "Cave_SDF_Main")
        
        result = await self.call_tool_async(
            "asset_mesh_editing_tool",
            action="generate_collision",
            asset_path=f"/Game/{actor_name}",
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Collision generation failed"),
                data={"raw_result": result},
            )

        return AgentResult(
            success=True,
            data={"collision": result},
        )

    async def _enable_nanite(self, context: AgentContext) -> AgentResult:
        """Enable Nanite on a mesh."""
        actor_name = context.metadata.get("actor_name", "Cave_SDF_Main")
        
        result = await self.call_tool_async(
            "asset_mesh_editing_tool",
            action="set_nanite_settings",
            asset_path=f"/Game/{actor_name}",
            enabled=True,
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Nanite enablement failed"),
                data={"raw_result": result},
            )

        return AgentResult(
            success=True,
            data={"nanite": result},
        )

    async def _unwrap_uv(self, context: AgentContext) -> AgentResult:
        """UV unwrap a mesh."""
        actor_name = context.metadata.get("actor_name", "Cave_SDF_Main")
        
        result = await self.call_tool_async(
            "asset_mesh_editing_tool",
            action="mesh_uv_unwrap",
            asset_path=f"/Game/{actor_name}",
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "UV unwrap failed"),
                data={"raw_result": result},
            )

        return AgentResult(
            success=True,
            data={"uv_unwrap": result},
        )

    async def _voxel_remesh(self, context: AgentContext) -> AgentResult:
        """Voxel remesh a mesh."""
        actor_name = context.metadata.get("actor_name", "Cave_SDF_Main")
        
        result = await self.call_tool_async(
            "asset_mesh_editing_tool",
            action="mesh_voxel_remesh",
            asset_path=f"/Game/{actor_name}",
            voxel_count=context.metadata.get("voxel_count", 100000),
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Voxel remesh failed"),
                data={"raw_result": result},
            )

        return AgentResult(
            success=True,
            data={"remesh": result},
        )
