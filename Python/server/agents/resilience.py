"""Resilience patterns for the agent system.

References:
- Circuit Breaker pattern (Martin Fowler)
- AWS Well-Architected Reliability Pillar

Circuit breakers prevent cascade failures by stopping requests to
unhealthy downstream services (Unreal TCP, scene-syncd HTTP, etc.).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, TypeVar

logger = logging.getLogger("agents.resilience")

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------


class CircuitOpenError(Exception):
    """Raised when a circuit breaker is open."""

    pass


@dataclass
class CircuitState:
    """Snapshot of circuit breaker state."""

    name: str
    state: str  # "closed" | "open" | "half-open"
    failure_count: int
    success_count: int
    last_failure_time: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
        }


class CircuitBreaker:
    """Circuit breaker for protecting tool/agent calls.

    States:
      - **closed**: Normal operation. Failures are counted.
      - **open**: Calls are rejected immediately. Waits for recovery_timeout.
      - **half-open**: One trial call is allowed. Success -> closed, failure -> open.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 1,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self._state = "closed"
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0

    @property
    def state(self) -> str:
        return self._state

    def get_state(self) -> CircuitState:
        return CircuitState(
            name=self.name,
            state=self._state,
            failure_count=self._failure_count,
            success_count=self._success_count,
            last_failure_time=self._last_failure_time,
        )

    def call(self, fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute ``fn`` through the circuit breaker.

        Raises:
            CircuitOpenError: if the circuit is open.
        """
        self._before_call()
        try:
            result = fn(*args, **kwargs)
            self._on_success()
            return result
        except Exception as exc:
            self._on_failure()
            raise

    async def call_async(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Async version of ``call``."""
        self._before_call()
        try:
            import asyncio

            if asyncio.iscoroutinefunction(fn):
                result = await fn(*args, **kwargs)
            else:
                result = fn(*args, **kwargs)
            self._on_success()
            return result
        except Exception as exc:
            self._on_failure()
            raise

    # ------------------------------------------------------------------
    # Internal state machine
    # ------------------------------------------------------------------

    def _before_call(self) -> None:
        if self._state == "open":
            if self._should_attempt_reset():
                self._state = "half-open"
                self._half_open_calls = 0
                logger.info("Circuit %s moved to half-open", self.name)
            else:
                raise CircuitOpenError(
                    f"Circuit '{self.name}' is OPEN. "
                    f"Last failure: {self._last_failure_time}"
                )

        if self._state == "half-open":
            if self._half_open_calls >= self.half_open_max_calls:
                raise CircuitOpenError(
                    f"Circuit '{self.name}' is half-open and max trial calls reached."
                )
            self._half_open_calls += 1

    def _on_success(self) -> None:
        if self._state == "half-open":
            self._reset()
            logger.info("Circuit %s recovered (closed)", self.name)
        else:
            self._success_count += 1

    def _on_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.perf_counter()

        if self._state == "half-open":
            self._state = "open"
            logger.warning(
                "Circuit %s opened (half-open trial failed)", self.name
            )
        elif self._failure_count >= self.failure_threshold:
            self._state = "open"
            logger.warning(
                "Circuit %s opened after %d failures",
                self.name,
                self._failure_count,
            )

    def _should_attempt_reset(self) -> bool:
        if self._last_failure_time is None:
            return True
        elapsed = time.perf_counter() - self._last_failure_time
        return elapsed >= self.recovery_timeout

    def _reset(self) -> None:
        self._state = "closed"
        self._failure_count = 0
        self._half_open_calls = 0
        self._last_failure_time = None

    def force_close(self) -> None:
        """Manually reset the circuit to closed (for admin/testing)."""
        self._reset()


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class CircuitBreakerRegistry:
    """Manages circuit breakers per tool/agent name."""

    def __init__(self) -> None:
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._default_threshold = 5
        self._default_timeout = 30.0

    def get(self, name: str) -> CircuitBreaker:
        """Get or create a circuit breaker for ``name``."""
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=self._default_threshold,
                recovery_timeout=self._default_timeout,
            )
        return self._breakers[name]

    def list_states(self) -> List[CircuitState]:
        return [cb.get_state() for cb in self._breakers.values()]

    def reset_all(self) -> None:
        for cb in self._breakers.values():
            cb.force_close()


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_registry_instance: Optional[CircuitBreakerRegistry] = None


def get_circuit_registry() -> CircuitBreakerRegistry:
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = CircuitBreakerRegistry()
    return _registry_instance


def reset_circuit_registry() -> None:
    global _registry_instance
    _registry_instance = None
