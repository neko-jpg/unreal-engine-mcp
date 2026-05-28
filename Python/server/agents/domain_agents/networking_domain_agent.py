"""Networking Domain Agent - Expert in multiplayer and networking."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from server.agents.base_agent import AgentContext, AgentResult, BaseAgent

logger = logging.getLogger("agents.networking_domain")


class NetworkingDomainAgent(BaseAgent):
    """Domain agent for networking and multiplayer operations.
    
    Capabilities:
    - Session creation
    - Session finding
    - Replication setup
    - RPC creation
    """

    name = "networking_domain"
    description = "Expert in multiplayer and networking"
    capabilities = [
        "network.session_create",
        "network.session_find",
        "network.session_join",
        "network.rpc_create",
        "network.replicate",
    ]
    domains = ["networking", "multiplayer", "online"]

    async def execute(self, intent: str, context: AgentContext) -> AgentResult:
        """Execute networking operations."""
        self.logger.info(f"NetworkingDomain executing: {intent[:80]}...")
        text_lower = intent.lower()

        if "session" in text_lower and "create" in text_lower:
            return await self._create_session(context)
        elif "find" in text_lower or "search" in text_lower:
            return await self._find_sessions(context)
        elif "join" in text_lower:
            return await self._join_session(context)
        elif "rpc" in text_lower:
            return await self._create_rpc(context)
        elif "replicate" in text_lower:
            return await self._setup_replication(context)
        else:
            return AgentResult(
                success=False,
                error=f"Unknown networking task: {intent}",
            )

    async def _create_session(self, context: AgentContext) -> AgentResult:
        """Create online session."""
        result = await self.call_tool_async(
            "create_session",
            session_name="GameSession",
            max_players=8,
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Session creation failed"),
            )

        return AgentResult(
            success=True,
            data={"session": result},
        )

    async def _find_sessions(self, context: AgentContext) -> AgentResult:
        """Find online sessions."""
        result = await self.call_tool_async(
            "find_sessions",
            timeout_seconds=10,
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Session find failed"),
            )

        return AgentResult(
            success=True,
            data={"sessions": result},
        )

    async def _join_session(self, context: AgentContext) -> AgentResult:
        """Join online session."""
        result = await self.call_tool_async(
            "join_session",
            session_name="GameSession",
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Session join failed"),
            )

        return AgentResult(
            success=True,
            data={"session": result},
        )

    async def _create_rpc(self, context: AgentContext) -> AgentResult:
        """Create RPC function."""
        result = await self.call_tool_async(
            "create_rpc_server_function",
            blueprint_path="/Game/Blueprints/BP_GameMode",
            function_name="ServerAction",
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "RPC creation failed"),
            )

        return AgentResult(
            success=True,
            data={"rpc": result},
        )

    async def _setup_replication(self, context: AgentContext) -> AgentResult:
        """Setup replication."""
        result = await self.call_tool_async(
            "set_actor_replicates",
            actor_name="ReplicatedActor",
            replicates=True,
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Replication setup failed"),
            )

        return AgentResult(
            success=True,
            data={"replication": result},
        )
