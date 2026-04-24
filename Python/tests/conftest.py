"""
Shared fixtures and utilities for Python-side tests.
All tests should be runnable without an actual Unreal Engine instance.
"""

import json
import socket
import threading
import time
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from unittest.mock import MagicMock

import pytest


PYTHON_ROOT = Path(__file__).resolve().parents[1]
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))


class FakeSocket:
    """
    A fake socket that can be injected into UnrealConnection for unit tests.
    Simulates recv fragmentation, timeouts, and arbitrary response payloads.
    """

    def __init__(
        self,
        response_payloads: Optional[List[bytes]] = None,
        chunk_size: int = 8192,
        timeout_after_recv: bool = False,
        recv_delay: float = 0.0,
        close_after_n_recv: Optional[int] = None,
        raise_on_connect: Optional[Exception] = None,
    ):
        self._responses = response_payloads or []
        self._chunk_size = chunk_size
        self._timeout_after_recv = timeout_after_recv
        self._recv_delay = recv_delay
        self._close_after_n_recv = close_after_n_recv
        self._raise_on_connect = raise_on_connect
        self._recv_count = 0
        self._buffer_index = 0
        self._shutdown = False
        self._closed = False
        self._opts: Dict[int, Any] = {}

    def connect(self, address):
        if self._raise_on_connect:
            raise self._raise_on_connect

    def settimeout(self, timeout):
        pass

    def setsockopt(self, level, optname, value):
        key = (level, optname)
        self._opts[key] = value

    def sendall(self, data: bytes) -> None:
        if self._closed:
            raise OSError("Socket is closed")
        self._last_sent = data

    def recv(self, bufsize: int) -> bytes:
        if self._closed:
            raise OSError("Socket is closed")

        self._recv_count += 1

        if self._recv_delay:
            time.sleep(self._recv_delay)

        if self._close_after_n_recv is not None and self._recv_count > self._close_after_n_recv:
            return b""

        if not self._responses:
            if self._timeout_after_recv:
                raise socket.timeout("Fake timeout")
            return b""

        payload = self._responses[0]
        start = self._buffer_index
        end = min(start + bufsize, len(payload))
        chunk = payload[start:end]
        self._buffer_index = end

        if self._buffer_index >= len(payload):
            self._responses.pop(0)
            self._buffer_index = 0

        return chunk

    def shutdown(self, how) -> None:
        self._shutdown = True

    def close(self) -> None:
        self._closed = True


class FakeUnrealConnection:
    """
    A minimal fake for send_command-based helper tests.
    Record what commands were sent and return pre-canned responses.
    """

    def __init__(self, responses: Optional[Dict[str, Any]] = None):
        self.responses = responses or {}
        self.history: List[Dict[str, Any]] = []

    def send_command(self, command: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.history.append({"command": command, "params": params or {}})
        key = (command, json.dumps(params or {}, sort_keys=True))
        if key in self.responses:
            return self.responses[key]
        if command in self.responses:
            return self.responses[command]
        # Default success for unknown commands
        return {"status": "success", "result": {}}

    def clear_history(self):
        self.history.clear()


@pytest.fixture
def fake_socket_factory() -> Callable[..., FakeSocket]:
    """Factory to create parameterized FakeSocket instances."""
    return FakeSocket


@pytest.fixture
def fake_conn_factory() -> Callable[..., FakeUnrealConnection]:
    """Factory to create parameterized FakeUnrealConnection instances."""
    return FakeUnrealConnection


@pytest.fixture
def fake_conn(fake_conn_factory) -> FakeUnrealConnection:
    """Simple FakeUnrealConnection instance with default success responses."""
    return fake_conn_factory()


@pytest.fixture(autouse=True)
def reset_singletons():
    """
    Reset global singletons between tests to avoid cross-test pollution.
    """
    import server.core as srv
    import helpers.actor_name_manager as anm

    with srv._connection_lock:
        srv._unreal_connection = None

    anm.clear_actor_cache()
    yield

    with srv._connection_lock:
        srv._unreal_connection = None
    anm.clear_actor_cache()
