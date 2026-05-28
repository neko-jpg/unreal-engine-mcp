"""Cinematic Domain Agent - Expert in cameras, sequencer, and rendering."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from server.agents.base_agent import AgentContext, AgentResult, BaseAgent

logger = logging.getLogger("agents.cinematic_domain")


class CinematicDomainAgent(BaseAgent):
    """Domain agent for cinematic and camera operations.
    
    Capabilities:
    - Camera setup and movement
    - Sequencer creation
    - Render queue setup
    - Shot composition
    """

    name = "cinematic_domain"
    description = "Expert in cinematic cameras and sequencer"
    capabilities = [
        "camera.spawn",
        "camera.move",
        "sequencer.create",
        "sequencer.add_track",
        "render.setup",
    ]
    domains = ["cinematic", "camera", "rendering"]

    async def execute(self, intent: str, context: AgentContext) -> AgentResult:
        """Execute cinematic operations."""
        self.logger.info(f"CinematicDomain executing: {intent[:80]}...")
        text_lower = intent.lower()

        if "camera" in text_lower:
            return await self._setup_camera(context)
        elif "sequencer" in text_lower or "sequence" in text_lower:
            return await self._create_sequence(context)
        elif "render" in text_lower:
            return await self._setup_render(context)
        else:
            return AgentResult(
                success=False,
                error=f"Unknown cinematic task: {intent}",
            )

    async def _setup_camera(self, context: AgentContext) -> AgentResult:
        """Setup cinematic camera."""
        result = await self.call_tool_async(
            "spawn_cine_camera_actor",
            name="CinematicCamera",
            location=[0, -500, 200],
            rotation=[-10, 0, 0],
            focal_length=35,
            aperture=2.8,
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Camera setup failed"),
            )

        return AgentResult(
            success=True,
            data={"camera": result},
        )

    async def _create_sequence(self, context: AgentContext) -> AgentResult:
        """Create sequencer sequence."""
        result = await self.call_tool_async(
            "create_level_sequence",
            sequence_path="/Game/Cinematics/Sequence_001",
            duration_frames=150,
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Sequence creation failed"),
            )

        return AgentResult(
            success=True,
            data={"sequence": result},
        )

    async def _setup_render(self, context: AgentContext) -> AgentResult:
        """Setup render queue."""
        result = await self.call_tool_async(
            "create_mrq_job",
            job_name="CinematicRender",
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Render setup failed"),
            )

        return AgentResult(
            success=True,
            data={"render": result},
        )
