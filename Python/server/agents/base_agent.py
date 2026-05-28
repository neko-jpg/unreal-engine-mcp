"""Base agent classes for the Unreal MCP agent architecture."""

from __future__ import annotations

import asyncio
import inspect
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar

from server.agents.guardrails import Guardrails, GuardrailResult
from server.agents.resilience import CircuitBreaker, CircuitOpenError, get_circuit_registry
from server.agents.tracing import AgentTracer, get_tracer, is_tracing_enabled

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    """Standard result structure for all agent operations."""
    success: bool = True
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    sub_results: List["AgentResult"] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "warnings": self.warnings,
            "metrics": self.metrics,
            "sub_results": [r.to_dict() for r in self.sub_results],
        }


@dataclass
class AgentContext:
    """Context passed through agent execution chain."""
    scene_id: str = "main"
    user_intent: str = ""
    target: Optional[str] = None
    style_profile: Optional[str] = None
    constraints: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_agent: Optional[str] = None
    depth: int = 0

    def fork(self, agent_name: str) -> "AgentContext":
        """Create a child context for sub-agent execution."""
        return AgentContext(
            scene_id=self.scene_id,
            user_intent=self.user_intent,
            target=self.target,
            style_profile=self.style_profile,
            constraints=dict(self.constraints),
            metadata=dict(self.metadata),
            parent_agent=agent_name,
            depth=self.depth + 1,
        )


class BaseAgent(ABC):
    """Base class for all agents in the system.
    
    Agents are hierarchical:
    - MasterOrchestrator (top level)
    - DomainAgents (middle level: Cave, Architecture, Lighting, etc.)
    - WorkerAgents (bottom level: Procedural, PCG, Mesh, Nav, etc.)
    """

    name: str = "base_agent"
    description: str = "Base agent class"
    capabilities: List[str] = []
    domains: List[str] = []
    max_depth: int = 5

    def __init__(self, tool_registry: Optional[Dict[str, Callable]] = None) -> None:
        self.tool_registry = tool_registry or {}
        self.sub_agents: Dict[str, BaseAgent] = {}
        self.logger = logging.getLogger(f"agents.{self.name}")
        self._tracer = get_tracer()
        self._current_span: Optional[Any] = None

    def register_sub_agent(self, agent: "BaseAgent") -> None:
        """Register a sub-agent for delegation."""
        self.sub_agents[agent.name] = agent
        self.logger.debug(f"Registered sub-agent: {agent.name}")

    def get_sub_agent(self, name: str) -> Optional["BaseAgent"]:
        """Get a registered sub-agent by name."""
        return self.sub_agents.get(name)

    def has_capability(self, capability_id: str) -> bool:
        """Check if this agent handles a specific capability."""
        return capability_id in self.capabilities

    def has_domain(self, domain: str) -> bool:
        """Check if this agent handles a specific domain."""
        return domain in self.domains

    @abstractmethod
    async def execute(self, intent: str, context: AgentContext) -> AgentResult:
        """Execute the agent's primary function.
        
        Args:
            intent: Natural language intent or command
            context: Execution context
            
        Returns:
            AgentResult with operation results
        """
        pass

    async def delegate(
        self,
        agent_name: str,
        intent: str,
        context: AgentContext,
    ) -> AgentResult:
        """Delegate execution to a sub-agent.
        
        Args:
            agent_name: Name of the sub-agent
            intent: Intent to pass to sub-agent
            context: Current context
            
        Returns:
            AgentResult from sub-agent
        """
        if context.depth >= self.max_depth:
            return AgentResult(
                success=False,
                error=f"Max agent depth ({self.max_depth}) exceeded",
            )

        agent = self.get_sub_agent(agent_name)
        if agent is None:
            return AgentResult(
                success=False,
                error=f"Sub-agent '{agent_name}' not found",
            )

        child_context = context.fork(agent.name)
        self.logger.info(
            f"Delegating to {agent_name} at depth {child_context.depth}: {intent[:60]}..."
        )

        # Tracing
        parent_span = self._current_span
        span = None
        if is_tracing_enabled(context.constraints):
            span = self._tracer.start_span(
                f"agent.delegate.{agent_name}",
                self.name,
                parent_id=parent_span.span_id if parent_span else None,
            )
            self._current_span = span
            self._tracer.log_delegate(span, self.name, agent_name, intent)

        try:
            result = await agent.execute(intent, child_context)
            result.sub_results = []  # Flatten at this level
            # Auto-propagate result into parent context metadata
            context.metadata[f"{agent_name}_result"] = result.to_dict()
            context.metadata[f"last_delegate_result"] = result.to_dict()
            return result
        except Exception as exc:
            self.logger.exception(f"Sub-agent {agent_name} failed")
            return AgentResult(
                success=False,
                error=f"{agent_name} execution failed: {exc}",
            )
        finally:
            if span is not None:
                self._tracer.finish_span(span)
                self._current_span = parent_span

    def call_tool(self, tool_name: str, **kwargs: Any) -> Dict[str, Any]:
        """Call an MCP tool by name.
        
        Args:
            tool_name: Name of the registered tool
            **kwargs: Tool arguments
            
        Returns:
            Tool result dictionary
        """
        tool = self.tool_registry.get(tool_name)
        if tool is None:
            return {"success": False, "error": f"Tool '{tool_name}' not found"}

        try:
            if asyncio.iscoroutinefunction(tool):
                # We'll need an event loop - this is a simplified version
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Can't run in running loop, return error
                    return {"success": False, "error": "Async tool called from running loop"}
                return loop.run_until_complete(tool(**kwargs))
            else:
                return tool(**kwargs)
        except Exception as exc:
            self.logger.exception(f"Tool {tool_name} failed")
            return {"success": False, "error": f"{tool_name} failed: {exc}"}

    async def call_tool_async(
        self,
        tool_name: str,
        constraints: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Async version of call_tool.

        If ``constraints["guardrails"]`` is truthy, runs ToolGuardrail before
        invoking the tool.
        """
        # Guardrails check
        if constraints is not None:
            gr = Guardrails.check_tool(tool_name, kwargs, constraints)
            if not gr.passed:
                violations = "; ".join(f"{v.guardrail}: {v.message}" for v in gr.violations)
                self.logger.warning(f"Tool guardrail blocked {tool_name}: {violations}")
                return {"success": False, "error": f"Guardrail blocked: {violations}"}

        tool = self.tool_registry.get(tool_name)
        if tool is None:
            return {"success": False, "error": f"Tool '{tool_name}' not found"}

        # Circuit breaker
        cb = get_circuit_registry().get(tool_name)
        try:
            if asyncio.iscoroutinefunction(tool):
                result = await cb.call_async(tool, **kwargs)
            else:
                result = cb.call(tool, **kwargs)
            # Tracing
            if self._current_span is not None:
                self._tracer.log_tool_call(self._current_span, tool_name, kwargs, result)
            return result
        except CircuitOpenError:
            self.logger.warning(f"Circuit breaker open for tool {tool_name}")
            return {"success": False, "error": f"Circuit breaker open for '{tool_name}'"}
        except Exception as exc:
            self.logger.exception(f"Tool {tool_name} failed")
            return {"success": False, "error": f"{tool_name} failed: {exc}"}

    def _merge_results(self, results: List[AgentResult]) -> AgentResult:
        """Merge multiple agent results into one."""
        merged = AgentResult()
        merged.sub_results = results
        merged.success = all(r.success for r in results)
        
        for r in results:
            if r.error:
                merged.warnings.append(r.error)
            merged.warnings.extend(r.warnings)
            merged.data.update(r.data)
            merged.metrics.update(r.metrics)
        
        return merged


class ToolRegistry:
    """Central registry for all MCP tools available to agents."""

    def __init__(self) -> None:
        self._tools: Dict[str, Callable] = {}
        self._domains: Dict[str, List[str]] = {}

    def register(self, name: str, func: Callable, domains: Optional[List[str]] = None) -> None:
        """Register a tool."""
        self._tools[name] = func
        if domains:
            for domain in domains:
                self._domains.setdefault(domain, []).append(name)

    def get(self, name: str) -> Optional[Callable]:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_by_domain(self, domain: str) -> List[str]:
        """List tools for a domain."""
        return list(self._domains.get(domain, []))

    def list_all(self) -> List[str]:
        """List all registered tools."""
        return list(self._tools.keys())

    def create_dict(self) -> Dict[str, Callable]:
        """Create a plain dict for agent use."""
        return dict(self._tools)


# Singleton registry instance
_tool_registry_instance: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry."""
    global _tool_registry_instance
    if _tool_registry_instance is None:
        _tool_registry_instance = ToolRegistry()
    return _tool_registry_instance


def reset_tool_registry() -> None:
    """Reset the global tool registry."""
    global _tool_registry_instance
    _tool_registry_instance = None
