"""Asset Management Domain Agent - Expert in content browser operations."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from server.agents.base_agent import AgentContext, AgentResult, BaseAgent

logger = logging.getLogger("agents.asset_management_domain")


class AssetManagementDomainAgent(BaseAgent):
    """Domain agent for asset management operations.
    
    Capabilities:
    - Folder creation
    - Asset listing
    - Asset movement
    - Redirector fixing
    """

    name = "asset_management_domain"
    description = "Expert in content browser and asset management"
    capabilities = [
        "asset.create_folder",
        "asset.list",
        "asset.move",
        "asset.delete",
        "asset.fix_redirectors",
    ]
    domains = ["asset_management", "content_browser"]

    async def execute(self, intent: str, context: AgentContext) -> AgentResult:
        """Execute asset management operations."""
        self.logger.info(f"AssetManagementDomain executing: {intent[:80]}...")
        text_lower = intent.lower()

        if "folder" in text_lower:
            return await self._create_folder(context)
        elif "list" in text_lower:
            return await self._list_assets(context)
        elif "move" in text_lower:
            return await self._move_asset(context)
        elif "delete" in text_lower:
            return await self._delete_asset(context)
        elif "redirector" in text_lower:
            return await self._fix_redirectors(context)
        else:
            return AgentResult(
                success=False,
                error=f"Unknown asset management task: {intent}",
            )

    async def _create_folder(self, context: AgentContext) -> AgentResult:
        """Create folder."""
        folder_path = context.metadata.get("folder_path", "/Game/NewFolder")
        
        result = await self.call_tool_async(
            "asset_management_tool",
            action="create_folder",
            folder_path=folder_path,
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Folder creation failed"),
            )

        return AgentResult(
            success=True,
            data={"folder": result},
        )

    async def _list_assets(self, context: AgentContext) -> AgentResult:
        """List assets."""
        folder_path = context.metadata.get("folder_path", "/Game")
        
        result = await self.call_tool_async(
            "asset_management_tool",
            action="list_assets",
            folder_path=folder_path,
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Asset listing failed"),
            )

        return AgentResult(
            success=True,
            data={"assets": result},
        )

    async def _move_asset(self, context: AgentContext) -> AgentResult:
        """Move asset."""
        source_path = context.metadata.get("source_path", "/Game/Old/Mesh")
        dest_path = context.metadata.get("dest_path", "/Game/New/Mesh")
        
        result = await self.call_tool_async(
            "asset_management_tool",
            action="move_asset",
            source_path=source_path,
            dest_path=dest_path,
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Asset move failed"),
            )

        return AgentResult(
            success=True,
            data={"move": result},
        )

    async def _delete_asset(self, context: AgentContext) -> AgentResult:
        """Delete asset."""
        asset_path = context.metadata.get("asset_path", "/Game/Temp/Mesh")
        
        result = await self.call_tool_async(
            "asset_management_tool",
            action="delete_asset",
            asset_path=asset_path,
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Asset deletion failed"),
            )

        return AgentResult(
            success=True,
            data={"delete": result},
        )

    async def _fix_redirectors(self, context: AgentContext) -> AgentResult:
        """Fix redirectors."""
        result = await self.call_tool_async(
            "asset_management_tool",
            action="fixup_redirectors",
            folder_path="/Game",
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Redirector fix failed"),
            )

        return AgentResult(
            success=True,
            data={"redirectors": result},
        )
