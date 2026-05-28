"""Gameplay Domain Agent - Expert in game mechanics and GAS."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from server.agents.base_agent import AgentContext, AgentResult, BaseAgent

logger = logging.getLogger("agents.gameplay_domain")


class GameplayDomainAgent(BaseAgent):
    """Domain agent for gameplay and Gameplay Ability System operations.
    
    Capabilities:
    - GameMode setup
    - Character creation
    - Ability granting
    - Save game management
    """

    name = "gameplay_domain"
    description = "Expert in game mechanics and abilities"
    capabilities = [
        "gameplay.create_gamemode",
        "gameplay.create_character",
        "gameplay.grant_ability",
        "gameplay.save_game",
    ]
    domains = ["gameplay", "gas", "abilities"]

    async def execute(self, intent: str, context: AgentContext) -> AgentResult:
        """Execute gameplay operations."""
        self.logger.info(f"GameplayDomain executing: {intent[:80]}...")
        text_lower = intent.lower()

        if "gamemode" in text_lower:
            return await self._create_gamemode(context)
        elif "character" in text_lower:
            return await self._create_character(context)
        elif "ability" in text_lower:
            return await self._grant_ability(context)
        elif "save" in text_lower:
            return await self._save_game(context)
        else:
            return AgentResult(
                success=False,
                error=f"Unknown gameplay task: {intent}",
            )

    async def _create_gamemode(self, context: AgentContext) -> AgentResult:
        """Create GameMode."""
        result = await self.call_tool_async(
            "create_gamemode_blueprint",
            name="BP_GameMode",
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "GameMode creation failed"),
            )

        return AgentResult(
            success=True,
            data={"gamemode": result},
        )

    async def _create_character(self, context: AgentContext) -> AgentResult:
        """Create character."""
        result = await self.call_tool_async(
            "create_character",
            name="BP_PlayerCharacter",
            add_movement_component=True,
            max_walk_speed=600,
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Character creation failed"),
            )

        return AgentResult(
            success=True,
            data={"character": result},
        )

    async def _grant_ability(self, context: AgentContext) -> AgentResult:
        """Grant ability to actor."""
        result = await self.call_tool_async(
            "grant_ability",
            actor_name="BP_PlayerCharacter",
            ability_path="/Game/Abilities/GA_Jump",
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Ability grant failed"),
            )

        return AgentResult(
            success=True,
            data={"ability": result},
        )

    async def _save_game(self, context: AgentContext) -> AgentResult:
        """Save game."""
        result = await self.call_tool_async(
            "save_game_to_slot",
            slot_name="save0",
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Save game failed"),
            )

        return AgentResult(
            success=True,
            data={"save": result},
        )
