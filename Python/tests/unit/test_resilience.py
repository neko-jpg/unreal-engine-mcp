"""Tests for the resilience (circuit breaker) module."""

from __future__ import annotations

import time

import pytest

from server.agents.resilience import (
    CircuitBreaker,
    CircuitBreakerRegistry,
    CircuitOpenError,
    get_circuit_registry,
    reset_circuit_registry,
)


class TestCircuitBreaker:
    """Test CircuitBreaker state machine."""

    def test_closed_allows_calls(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        result = cb.call(lambda: 42)
        assert result == 42
        assert cb.state == "closed"

    def test_opens_after_failures(self):
        cb = CircuitBreaker("test", failure_threshold=2)
        with pytest.raises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        assert cb.state == "closed"
        assert cb._failure_count == 1

        with pytest.raises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        assert cb.state == "open"
        assert cb._failure_count == 2

    def test_open_blocks_calls(self):
        cb = CircuitBreaker("test", failure_threshold=1)
        with pytest.raises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        assert cb.state == "open"

        with pytest.raises(CircuitOpenError):
            cb.call(lambda: 42)

    def test_half_open_recovery(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.1)
        with pytest.raises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        assert cb.state == "open"

        time.sleep(0.15)
        # Half-open allows one trial
        result = cb.call(lambda: 42)
        assert result == 42
        assert cb.state == "closed"

    def test_half_open_failure_reopens(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.1)
        with pytest.raises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("boom")))

        time.sleep(0.15)
        with pytest.raises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        assert cb.state == "open"

    def test_force_close(self):
        cb = CircuitBreaker("test", failure_threshold=1)
        with pytest.raises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        assert cb.state == "open"
        cb.force_close()
        assert cb.state == "closed"
        result = cb.call(lambda: 42)
        assert result == 42

    def test_get_state(self):
        cb = CircuitBreaker("test", failure_threshold=2)
        state = cb.get_state()
        assert state.name == "test"
        assert state.state == "closed"
        assert state.failure_count == 0

    @pytest.mark.asyncio
    async def test_call_async(self):
        cb = CircuitBreaker("async_test")

        async def async_fn():
            return 42

        result = await cb.call_async(async_fn)
        assert result == 42


class TestCircuitBreakerRegistry:
    """Test CircuitBreakerRegistry."""

    def setup_method(self):
        reset_circuit_registry()

    def test_get_or_create(self):
        reg = get_circuit_registry()
        cb1 = reg.get("tool_a")
        cb2 = reg.get("tool_a")
        assert cb1 is cb2

    def test_list_states(self):
        reg = get_circuit_registry()
        reg.get("tool_a")
        reg.get("tool_b")
        states = reg.list_states()
        assert len(states) == 2

    def test_reset_all(self):
        reg = get_circuit_registry()
        cb = reg.get("tool_a")
        cb._state = "open"
        reg.reset_all()
        assert cb.state == "closed"
