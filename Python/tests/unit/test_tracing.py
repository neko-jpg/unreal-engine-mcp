"""Tests for the tracing module."""

from __future__ import annotations

import time

import pytest

from server.agents.tracing import (
    AgentTracer,
    Span,
    Trace,
    TracingConfig,
    get_tracer,
    is_tracing_enabled,
    reset_tracer,
)


class TestSpan:
    """Test Span dataclass."""

    def test_duration_ms(self):
        span = Span(
            span_id="abc",
            name="test",
            agent_type="test_agent",
            start_time=time.perf_counter(),
        )
        assert span.duration_ms() is None
        span.end_time = span.start_time + 0.1
        assert span.duration_ms() is not None
        assert span.duration_ms() >= 95.0  # allow for floating point variance

    def test_to_dict(self):
        span = Span(
            span_id="abc",
            name="test",
            agent_type="test_agent",
            start_time=0.0,
            end_time=1.0,
            attributes={"key": "value"},
        )
        d = span.to_dict()
        assert d["span_id"] == "abc"
        assert d["name"] == "test"
        assert d["duration_ms"] == 1000.0
        assert d["attributes"]["key"] == "value"


class TestAgentTracer:
    """Test AgentTracer."""

    def setup_method(self):
        reset_tracer()

    def test_start_and_finish_span(self):
        tracer = AgentTracer()
        span = tracer.start_span("agent.workflow.test", "test_agent")
        assert span.span_id in tracer._active_spans
        tracer.finish_span(span)
        assert span.span_id not in tracer._active_spans
        assert span.end_time is not None

    def test_log_tool_call(self):
        tracer = AgentTracer()
        span = tracer.start_span("test", "test_agent")
        tracer.log_tool_call(
            span,
            "set_light_intensity",
            {"intensity": 100.0},
            {"success": True},
        )
        assert len(span.events) == 1
        assert span.events[0]["name"] == "mcp.tool.set_light_intensity"

    def test_log_delegate(self):
        tracer = AgentTracer()
        span = tracer.start_span("test", "orchestrator")
        tracer.log_delegate(span, "orchestrator", "lighting_domain", "dark lighting")
        assert len(span.events) == 1
        assert span.events[0]["name"] == "agent.delegate.lighting_domain"

    def test_parent_child_relationship(self):
        tracer = AgentTracer()
        parent = tracer.start_span("parent", "orchestrator")
        child = tracer.start_span("child", "domain", parent_id=parent.span_id)
        assert child.parent_id == parent.span_id


class TestTracingConfig:
    """Test tracing configuration."""

    def test_disabled_by_default(self):
        TracingConfig.enabled = False
        assert is_tracing_enabled() is False
        assert is_tracing_enabled({}) is False

    def test_global_enable(self):
        TracingConfig.enabled = True
        assert is_tracing_enabled() is True
        TracingConfig.enabled = False

    def test_constraints_enable(self):
        TracingConfig.enabled = False
        assert is_tracing_enabled({"tracing": True}) is True
        assert is_tracing_enabled({"tracing": {"enabled": True}}) is True
        assert is_tracing_enabled({"tracing": {"enabled": False}}) is False

    def test_get_tracer_singleton(self):
        reset_tracer()
        t1 = get_tracer()
        t2 = get_tracer()
        assert t1 is t2
