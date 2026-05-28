"""Project Editor Domain Agent - Expert in project settings and editor control."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from server.agents.base_agent import AgentContext, AgentResult, BaseAgent

logger = logging.getLogger("agents.project_editor_domain")


class ProjectEditorDomainAgent(BaseAgent):
    """Domain agent for project and editor operations.
    
    Capabilities:
    - Project settings
    - Plugin management
    - Editor preferences
    - Build and package
    """

    name = "project_editor_domain"
    description = "Expert in project settings and editor control"
    capabilities = [
        "project.settings",
        "project.plugins",
        "editor.preferences",
        "build.compile",
        "package.build",
    ]
    domains = ["project_editor", "settings", "build"]

    async def execute(self, intent: str, context: AgentContext) -> AgentResult:
        """Execute project editor operations."""
        self.logger.info(f"ProjectEditorDomain executing: {intent[:80]}...")
        text_lower = intent.lower()

        if "settings" in text_lower or "config" in text_lower:
            return await self._update_settings(context)
        elif "plugin" in text_lower:
            return await self._manage_plugins(context)
        elif "build" in text_lower or "compile" in text_lower:
            return await self._build_project(context)
        elif "package" in text_lower:
            return await self._package_project(context)
        else:
            return AgentResult(
                success=False,
                error=f"Unknown project editor task: {intent}",
            )

    async def _update_settings(self, context: AgentContext) -> AgentResult:
        """Update project settings."""
        result = await self.call_tool_async(
            "project_settings_tool",
            action="set",
            file="DefaultEngine.ini",
            section="/Script/Engine.RendererSettings",
            key="r.DefaultFeature.AutoExposure",
            value="True",
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Settings update failed"),
            )

        return AgentResult(
            success=True,
            data={"settings": result},
        )

    async def _manage_plugins(self, context: AgentContext) -> AgentResult:
        """Manage plugins."""
        result = await self.call_tool_async(
            "plugin_tool",
            action="list",
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Plugin management failed"),
            )

        return AgentResult(
            success=True,
            data={"plugins": result},
        )

    async def _build_project(self, context: AgentContext) -> AgentResult:
        """Build project."""
        result = await self.call_tool_async(
            "build_project",
            platform="Win64",
            configuration="Development",
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Build failed"),
            )

        return AgentResult(
            success=True,
            data={"build": result},
        )

    async def _package_project(self, context: AgentContext) -> AgentResult:
        """Package project."""
        result = await self.call_tool_async(
            "package_for_platform",
            platform="Win64",
            configuration="Shipping",
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Package failed"),
            )

        return AgentResult(
            success=True,
            data={"package": result},
        )
