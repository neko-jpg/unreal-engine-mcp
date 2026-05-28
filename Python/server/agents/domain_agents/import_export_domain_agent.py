"""Import/Export Domain Agent - Expert in asset importing and exporting."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from server.agents.base_agent import AgentContext, AgentResult, BaseAgent

logger = logging.getLogger("agents.import_export_domain")


class ImportExportDomainAgent(BaseAgent):
    """Domain agent for import and export operations.
    
    Capabilities:
    - FBX import
    - Texture import
    - Audio import
    - Asset export
    """

    name = "import_export_domain"
    description = "Expert in asset importing and exporting"
    capabilities = [
        "import.fbx",
        "import.texture",
        "import.audio",
        "export.asset",
    ]
    domains = ["import_export", "assets"]

    async def execute(self, intent: str, context: AgentContext) -> AgentResult:
        """Execute import/export operations."""
        self.logger.info(f"ImportExportDomain executing: {intent[:80]}...")
        text_lower = intent.lower()

        if "fbx" in text_lower or "mesh" in text_lower:
            return await self._import_fbx(context)
        elif "texture" in text_lower or "image" in text_lower:
            return await self._import_texture(context)
        elif "audio" in text_lower or "sound" in text_lower:
            return await self._import_audio(context)
        elif "export" in text_lower:
            return await self._export_asset(context)
        else:
            return AgentResult(
                success=False,
                error=f"Unknown import/export task: {intent}",
            )

    async def _import_fbx(self, context: AgentContext) -> AgentResult:
        """Import FBX mesh."""
        source_path = context.metadata.get("source_path", "C:/Models/mesh.fbx")
        destination_path = context.metadata.get("destination_path", "/Game/Imported")
        
        result = await self.call_tool_async(
            "fbx_mesh_import_tool",
            source_path=source_path,
            destination_path=destination_path,
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "FBX import failed"),
            )

        return AgentResult(
            success=True,
            data={"import": result},
        )

    async def _import_texture(self, context: AgentContext) -> AgentResult:
        """Import texture."""
        source_path = context.metadata.get("source_path", "C:/Textures/texture.png")
        destination_path = context.metadata.get("destination_path", "/Game/Textures")
        
        result = await self.call_tool_async(
            "texture_import_tool",
            source_path=source_path,
            destination_path=destination_path,
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Texture import failed"),
            )

        return AgentResult(
            success=True,
            data={"import": result},
        )

    async def _import_audio(self, context: AgentContext) -> AgentResult:
        """Import audio."""
        source_path = context.metadata.get("source_path", "C:/Audio/sound.wav")
        destination_path = context.metadata.get("destination_path", "/Game/Audio")
        
        result = await self.call_tool_async(
            "audio_import_tool",
            source_path=source_path,
            destination_path=destination_path,
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Audio import failed"),
            )

        return AgentResult(
            success=True,
            data={"import": result},
        )

    async def _export_asset(self, context: AgentContext) -> AgentResult:
        """Export asset."""
        asset_path = context.metadata.get("asset_path", "/Game/Imported/Mesh")
        output_path = context.metadata.get("output_path", "C:/Exports/mesh.fbx")
        
        result = await self.call_tool_async(
            "asset_export_tool",
            asset_path=asset_path,
            output_path=output_path,
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Asset export failed"),
            )

        return AgentResult(
            success=True,
            data={"export": result},
        )
