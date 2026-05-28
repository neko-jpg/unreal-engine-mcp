"""Level Management Domain Agent - Expert in levels, maps, and world partition."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from server.agents.base_agent import AgentContext, AgentResult, BaseAgent

logger = logging.getLogger("agents.level_management_domain")


class LevelManagementDomainAgent(BaseAgent):
    """Domain agent for level and map operations.
    
    Capabilities:
    - Level creation/loading
    - Sublevel management
    - World partition setup
    - Streaming configuration
    """

    name = "level_management_domain"
    description = "Expert in level and world management"
    capabilities = [
        "level.create",
        "level.load",
        "level.save",
        "sublevel.add",
        "world_partition.enable",
    ]
    domains = ["level_management", "world", "map"]

    async def execute(self, intent: str, context: AgentContext) -> AgentResult:
        """Execute level management operations."""
        self.logger.info(f"LevelManagementDomain executing: {intent[:80]}...")
        text_lower = intent.lower()

        if "create" in text_lower:
            return await self._create_level(context)
        elif "load" in text_lower:
            return await self._load_level(context)
        elif "save" in text_lower:
            return await self._save_level(context)
        elif "sublevel" in text_lower:
            return await self._add_sublevel(context)
        elif "partition" in text_lower:
            return await self._setup_world_partition(context)
        else:
            return AgentResult(
                success=False,
                error=f"Unknown level management task: {intent}",
            )

    async def _create_level(self, context: AgentContext) -> AgentResult:
        """Create new level."""
        result = await self.call_tool_async(
            "level_tool",
            action="create",
            asset_path="/Game/Maps/NewLevel",
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Level creation failed"),
            )

        return AgentResult(
            success=True,
            data={"level": result},
        )

    async def _load_level(self, context: AgentContext) -> AgentResult:
        """Load level."""
        level_path = context.metadata.get("level_path", "/Game/Maps/Main")
        
        result = await self.call_tool_async(
            "level_tool",
            action="load",
            asset_path=level_path,
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Level load failed"),
            )

        return AgentResult(
            success=True,
            data={"level": result},
        )

    async def _save_level(self, context: AgentContext) -> AgentResult:
        """Save level."""
        result = await self.call_tool_async(
            "level_tool",
            action="save",
            asset_path="/Game/Maps/Main",
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Level save failed"),
            )

        return AgentResult(
            success=True,
            data={"level": result},
        )

    async def _add_sublevel(self, context: AgentContext) -> AgentResult:
        """Add sublevel."""
        level_path = context.metadata.get("level_path", "/Game/Maps/SubLevel")
        
        result = await self.call_tool_async(
            "sublevel_tool",
            action="add",
            level_path=level_path,
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Sublevel add failed"),
            )

        return AgentResult(
            success=True,
            data={"sublevel": result},
        )

    async def _setup_world_partition(self, context: AgentContext) -> AgentResult:
        """Setup world partition."""
        result = await self.call_tool_async(
            "world_partition_tool",
            action="enable",
            enable=True,
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "World partition setup failed"),
            )

        return AgentResult(
            success=True,
            data={"world_partition": result},
        )
