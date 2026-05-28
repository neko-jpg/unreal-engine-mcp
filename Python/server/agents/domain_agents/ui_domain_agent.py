"""UI Domain Agent - Expert in UMG widgets and user interface."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from server.agents.base_agent import AgentContext, AgentResult, BaseAgent

logger = logging.getLogger("agents.ui_domain")


class UiDomainAgent(BaseAgent):
    """Domain agent for UI/UMG operations.
    
    Capabilities:
    - Widget blueprint creation
    - UI element addition
    - Button/Text binding
    - HUD setup
    """

    name = "ui_domain"
    description = "Expert in UMG widgets and UI"
    capabilities = [
        "ui.create_widget",
        "ui.add_element",
        "ui.bind_event",
        "ui.setup_hud",
    ]
    domains = ["ui", "widget", "hud"]

    async def execute(self, intent: str, context: AgentContext) -> AgentResult:
        """Execute UI operations."""
        self.logger.info(f"UiDomain executing: {intent[:80]}...")
        text_lower = intent.lower()

        if "widget" in text_lower or "menu" in text_lower:
            return await self._create_widget(context)
        elif "hud" in text_lower:
            return await self._setup_hud(context)
        elif "button" in text_lower:
            return await self._add_button(context)
        else:
            return AgentResult(
                success=False,
                error=f"Unknown UI task: {intent}",
            )

    async def _create_widget(self, context: AgentContext) -> AgentResult:
        """Create widget blueprint."""
        result = await self.call_tool_async(
            "umg_tool",
            action="create_widget_blueprint",
            blueprint_path="/Game/UI/W_MainMenu",
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Widget creation failed"),
            )

        return AgentResult(
            success=True,
            data={"widget": result},
        )

    async def _setup_hud(self, context: AgentContext) -> AgentResult:
        """Setup HUD."""
        result = await self.call_tool_async(
            "set_hud_class",
            name="BP_HUD",
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "HUD setup failed"),
            )

        return AgentResult(
            success=True,
            data={"hud": result},
        )

    async def _add_button(self, context: AgentContext) -> AgentResult:
        """Add button to widget."""
        result = await self.call_tool_async(
            "umg_tool",
            action="add_widget",
            widget_blueprint="/Game/UI/W_MainMenu",
            widget_type="Button",
            widget_name="MainButton",
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Button addition failed"),
            )

        return AgentResult(
            success=True,
            data={"button": result},
        )
