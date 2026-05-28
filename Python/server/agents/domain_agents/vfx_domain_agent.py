"""VFX Domain Agent - Expert in Niagara and visual effects."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from server.agents.base_agent import AgentContext, AgentResult, BaseAgent

logger = logging.getLogger("agents.vfx_domain")


class VfxDomainAgent(BaseAgent):
    """Domain agent for VFX operations.
    
    Capabilities:
    - Niagara component addition
    - Particle parameter control
    - Color/spawn rate adjustments
    """

    name = "vfx_domain"
    description = "Expert in visual effects and particles"
    capabilities = [
        "vfx.add_niagara_component",
        "vfx.set_niagara_user_parameter",
        "vfx.set_niagara_color",
    ]
    domains = ["vfx", "particles", "niagara"]

    async def execute(self, intent: str, context: AgentContext) -> AgentResult:
        """Execute VFX operations."""
        self.logger.info(f"VfxDomain executing: {intent[:80]}...")
        text_lower = intent.lower()

        if "dust" in text_lower:
            return await self._add_dust_effect(context)
        elif "smoke" in text_lower:
            return await self._add_smoke_effect(context)
        elif "ember" in text_lower or "fire" in text_lower:
            return await self._add_fire_effect(context)
        elif "water" in text_lower or "drip" in text_lower:
            return await self._add_water_effect(context)
        else:
            return await self._add_default_effect(context)

    async def _add_dust_effect(self, context: AgentContext) -> AgentResult:
        """Add dust particle effect."""
        actor_name = context.metadata.get("actor_name", "Cave_SDF_Main")
        
        result = await self.call_tool_async(
            "add_niagara_component",
            actor_name=actor_name,
            system_path="/Game/MCP/VFX/dust",
            component_name="Cave_Dust",
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Dust effect failed"),
            )

        return AgentResult(
            success=True,
            data={"effect": "dust"},
        )

    async def _add_smoke_effect(self, context: AgentContext) -> AgentResult:
        """Add smoke particle effect."""
        actor_name = context.metadata.get("actor_name", "Cave_SDF_Main")
        
        result = await self.call_tool_async(
            "add_niagara_component",
            actor_name=actor_name,
            system_path="/Game/MCP/VFX/smoke",
            component_name="Cave_Smoke",
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Smoke effect failed"),
            )

        return AgentResult(
            success=True,
            data={"effect": "smoke"},
        )

    async def _add_fire_effect(self, context: AgentContext) -> AgentResult:
        """Add fire/ember particle effect."""
        actor_name = context.metadata.get("actor_name", "Cave_SDF_Main")
        
        result = await self.call_tool_async(
            "add_niagara_component",
            actor_name=actor_name,
            system_path="/Game/MCP/VFX/embers",
            component_name="Cave_Embers",
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Fire effect failed"),
            )

        return AgentResult(
            success=True,
            data={"effect": "embers"},
        )

    async def _add_water_effect(self, context: AgentContext) -> AgentResult:
        """Add water drip effect."""
        actor_name = context.metadata.get("actor_name", "Cave_SDF_Main")
        
        result = await self.call_tool_async(
            "add_niagara_component",
            actor_name=actor_name,
            system_path="/Game/MCP/VFX/drip",
            component_name="Cave_Drip",
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Water effect failed"),
            )

        return AgentResult(
            success=True,
            data={"effect": "drip"},
        )

    async def _add_default_effect(self, context: AgentContext) -> AgentResult:
        """Add default particle effect."""
        return AgentResult(
            success=True,
            data={"effect": "none"},
        )
