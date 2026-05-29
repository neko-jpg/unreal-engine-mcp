"""Audio Domain Agent - Expert in sound and ambient audio."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from server.agents.base_agent import AgentContext, AgentResult, BaseAgent

logger = logging.getLogger("agents.audio_domain")


class AudioDomainAgent(BaseAgent):
    """Domain agent for audio operations.
    
    Capabilities:
    - Ambient sound spawning
    - Audio component addition
    - Sound attenuation setup
    """

    name = "audio_domain"
    description = "Expert in audio and sound design"
    capabilities = [
        "audio.spawn_ambient",
        "audio.add_component",
        "audio.set_attenuation",
    ]
    domains = ["audio", "sound"]

    async def execute(self, intent: str, context: AgentContext) -> AgentResult:
        """Execute audio operations."""
        self.logger.info(f"AudioDomain executing: {intent[:80]}...")
        text_lower = intent.lower()

        if "ambient" in text_lower or "background" in text_lower:
            return await self._setup_ambient(context)
        elif "drip" in text_lower or "water" in text_lower:
            return await self._setup_drip_sound(context)
        elif "wind" in text_lower:
            return await self._setup_wind_sound(context)
        else:
            return await self._setup_default_audio(context)

    async def _setup_ambient(self, context: AgentContext) -> AgentResult:
        """Setup ambient cave sounds (best-effort)."""
        steps = []

        # Drip sound
        result = await self.call_tool_async(
            "spawn_ambient_sound",
            sound_path="/Game/MCP/Audio/drip",
            actor_name="Cave_Ambient_Drip",
            volume=0.35,
        )
        steps.append({"step": "drip", "result": result})

        # Wind sound
        result = await self.call_tool_async(
            "spawn_ambient_sound",
            sound_path="/Game/MCP/Audio/wind",
            actor_name="Cave_Ambient_Wind",
            volume=0.2,
        )
        steps.append({"step": "wind", "result": result})

        failures = [s for s in steps if s["result"].get("success") is False]

        return AgentResult(
            success=True,  # Best-effort: audio assets may not exist in project
            data={"audio_setup": "ambient", "steps": steps},
            warnings=[f"{s['step']}: {s['result'].get('error')}" for s in failures],
        )

    async def _setup_drip_sound(self, context: AgentContext) -> AgentResult:
        """Setup water drip sound."""
        result = await self.call_tool_async(
            "spawn_ambient_sound",
            sound_path="/Game/MCP/Audio/drip",
            actor_name="Cave_Drip",
            volume=0.4,
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Drip sound setup failed"),
            )

        return AgentResult(
            success=True,
            data={"sound": "drip"},
        )

    async def _setup_wind_sound(self, context: AgentContext) -> AgentResult:
        """Setup wind sound."""
        result = await self.call_tool_async(
            "spawn_ambient_sound",
            sound_path="/Game/MCP/Audio/wind",
            actor_name="Cave_Wind",
            volume=0.25,
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Wind sound setup failed"),
            )

        return AgentResult(
            success=True,
            data={"sound": "wind"},
        )

    async def _setup_default_audio(self, context: AgentContext) -> AgentResult:
        """Setup default audio."""
        return AgentResult(
            success=True,
            data={"sound": "default"},
        )
