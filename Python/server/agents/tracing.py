"""Tracing — OpenTelemetry-inspired agent execution observability.

References:
- OpenTelemetry AI Agent Observability Standards (2025)
- Semantic conventions:
  - agent.workflow.{step_name}
  - mcp.tool.{tool_name}
  - agent.delegate.{domain}

All tracing is **opt-in**.  Enable via:
  - ``context.constraints["tracing"] = True``  (per-request)
  - ``TracingConfig.enabled = True``            (global)
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("agents.tracing")


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class Span:
    """A single trace span."""

    span_id: str
    name: str
    agent_type: str
    start_time: float
    parent_id: Optional[str] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    end_time: Optional[float] = None

    def duration_ms(self) -> Optional[float]:
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time) * 1000.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "span_id": self.span_id,
            "name": self.name,
            "agent_type": self.agent_type,
            "parent_id": self.parent_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms(),
            "attributes": self.attributes,
            "events": self.events,
        }


@dataclass
class Trace:
    """A complete trace (tree of spans)."""

    trace_id: str
    spans: List[Span] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "spans": [s.to_dict() for s in self.spans],
        }


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


class TracingConfig:
    """Global tracing configuration."""

    enabled: bool = False
    max_spans_per_trace: int = 1000
    slow_threshold_ms: float = 5000.0


# ---------------------------------------------------------------------------
# Tracer
# ---------------------------------------------------------------------------


class AgentTracer:
    """In-memory tracer for agent executions.

    Follows OpenTelemetry semantic conventions where applicable:
    - Span names: ``agent.workflow.{step_name}``
    - Tool calls: ``mcp.tool.{tool_name}``
    - Delegation: ``agent.delegate.{domain}``
    """

    def __init__(self) -> None:
        self._active_spans: Dict[str, Span] = {}
        self._traces: Dict[str, Trace] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start_span(
        self,
        name: str,
        agent_type: str,
        parent_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Span:
        span = Span(
            span_id=str(uuid.uuid4())[:16],
            name=name,
            agent_type=agent_type,
            start_time=time.perf_counter(),
            parent_id=parent_id,
            attributes=dict(attributes or {}),
        )
        self._active_spans[span.span_id] = span
        return span

    def finish_span(self, span: Span) -> None:
        span.end_time = time.perf_counter()
        self._active_spans.pop(span.span_id, None)

        # Warn on slow spans
        duration = span.duration_ms()
        if duration is not None and duration > TracingConfig.slow_threshold_ms:
            logger.warning(
                "Slow span %s: %.1fms (agent=%s)",
                span.name,
                duration,
                span.agent_type,
            )

    def add_event(self, span: Span, event_name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        span.events.append(
            {
                "name": event_name,
                "timestamp": time.perf_counter(),
                "attributes": dict(attributes or {}),
            }
        )

    # ------------------------------------------------------------------
    # High-level helpers
    # ------------------------------------------------------------------

    def log_tool_call(
        self,
        span: Span,
        tool_name: str,
        params: Dict[str, Any],
        result: Any,
    ) -> None:
        self.add_event(
            span,
            f"mcp.tool.{tool_name}",
            {
                "tool_name": tool_name,
                "param_keys": list(params.keys()),
                "success": isinstance(result, dict) and result.get("success", True),
            },
        )

    def log_delegate(
        self,
        span: Span,
        from_agent: str,
        to_agent: str,
        intent: str,
    ) -> None:
        self.add_event(
            span,
            f"agent.delegate.{to_agent}",
            {
                "from_agent": from_agent,
                "to_agent": to_agent,
                "intent_preview": intent[:80],
            },
        )

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get_active_spans(self) -> List[Span]:
        return list(self._active_spans.values())

    def dump(self) -> List[Dict[str, Any]]:
        return [trace.to_dict() for trace in self._traces.values()]

    def clear(self) -> None:
        self._active_spans.clear()
        self._traces.clear()


# ---------------------------------------------------------------------------
# Singleton / convenience
# ---------------------------------------------------------------------------

_tracer_instance: Optional[AgentTracer] = None


def get_tracer() -> AgentTracer:
    global _tracer_instance
    if _tracer_instance is None:
        _tracer_instance = AgentTracer()
    return _tracer_instance


def reset_tracer() -> None:
    global _tracer_instance
    _tracer_instance = None


def is_tracing_enabled(constraints: Optional[Dict[str, Any]] = None) -> bool:
    if TracingConfig.enabled:
        return True
    if constraints:
        tracing = constraints.get("tracing")
        if isinstance(tracing, bool):
            return tracing
        if isinstance(tracing, dict):
            return tracing.get("enabled", False)
    return False
