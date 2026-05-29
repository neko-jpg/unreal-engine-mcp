"""Post Process Domain Agent - Expert in post-processing and camera effects."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from server.agents.base_agent import AgentContext, AgentResult, BaseAgent

logger = logging.getLogger("agents.postprocess_domain")


class PostProcessDomainAgent(BaseAgent):
    """Domain agent for post-processing operations.
    
    Capabilities:
    - Post process volume creation
    - Bloom, exposure, saturation setup
    - Color grading
    - Vignette and film grain
    """

    name = "postprocess_domain"
    description = "Expert in post-processing and camera effects"
    capabilities = [
        "postprocess.spawn",
        "postprocess.apply",
        "postprocess.set_bloom",
        "postprocess.set_exposure",
        "postprocess.set_saturation",
        "postprocess.set_contrast",
    ]
    domains = ["post_process", "camera", "effects"]

    async def execute(self, intent: str, context: AgentContext) -> AgentResult:
        """Execute post-process operations."""
        self.logger.info(f"PostProcessDomain executing: {intent[:80]}...")
        text_lower = intent.lower()

        if "creepy" in text_lower or "dark" in text_lower or "horror" in text_lower:
            return await self._create_creepy_postprocess(context)
        elif "bright" in text_lower or "warm" in text_lower:
            return await self._create_bright_postprocess(context)
        elif "bloom" in text_lower:
            return await self._setup_bloom(context)
        elif "exposure" in text_lower:
            return await self._setup_exposure(context)
        else:
            return await self._create_default_postprocess(context)

    def _get_spawned_name(self, result: Dict[str, Any], fallback: str) -> str:
        """Extract the actual UE actor name from a spawn response."""
        if not isinstance(result, dict):
            return fallback
        return result.get("actor_name") or result.get("name") or result.get("final_name") or fallback

    async def _create_creepy_postprocess(self, context: AgentContext) -> AgentResult:
        """Create creepy post-processing setup."""
        steps = []

        # Spawn post process volume
        result = await self.call_tool_async(
            "spawn_post_process_volume",
            name="MCP_PostProcess_Primary",
            infinite_extent=True,
        )
        steps.append({"step": "spawn", "result": result})
        pp_name = self._get_spawned_name(result, "MCP_PostProcess_Primary")

        # Configure post process (saturation/contrast not supported by this tool)
        result = await self.call_tool_async(
            "set_post_process_volume",
            volume_name=pp_name,
            bloom_intensity=0.4,
            vignette_intensity=0.35,
            color_temperature=4200.0,
        )
        steps.append({"step": "configure", "result": result})

        failures = [s for s in steps if s["result"].get("success") is False]

        return AgentResult(
            success=len(failures) < len(steps),
            data={"postprocess_setup": "creepy", "steps": steps},
            warnings=[f"{s['step']}: {s['result'].get('error')}" for s in failures],
        )

    async def _create_bright_postprocess(self, context: AgentContext) -> AgentResult:
        """Create bright post-processing setup."""
        result = await self.call_tool_async(
            "set_post_process_volume",
            volume_name="MCP_PostProcess_Primary",
            bloom_intensity=1.2,
            vignette_intensity=0.1,
            color_temperature=6500.0,
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Bright postprocess failed"),
            )

        return AgentResult(
            success=True,
            data={"postprocess_setup": "bright"},
        )

    async def _setup_bloom(self, context: AgentContext) -> AgentResult:
        """Setup bloom."""
        intensity = context.metadata.get("bloom_intensity", 0.5)
        
        result = await self.call_tool_async(
            "set_post_process_volume",
            volume_name="MCP_PostProcess_Primary",
            bloom_intensity=intensity,
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Bloom setup failed"),
            )

        return AgentResult(
            success=True,
            data={"bloom": intensity},
        )

    async def _setup_exposure(self, context: AgentContext) -> AgentResult:
        """Setup exposure."""
        bias = context.metadata.get("exposure_bias", 0.0)
        
        result = await self.call_tool_async(
            "set_post_process_volume",
            volume_name="MCP_PostProcess_Primary",
            exposure_bias=bias,
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Exposure setup failed"),
            )

        return AgentResult(
            success=True,
            data={"exposure": bias},
        )

    async def _create_default_postprocess(self, context: AgentContext) -> AgentResult:
        """Create default post-processing."""
        return AgentResult(
            success=True,
            data={"postprocess_setup": "default"},
        )
