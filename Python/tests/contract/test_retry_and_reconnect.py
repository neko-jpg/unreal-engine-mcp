"""
tests/contract/test_retry_and_reconnect.py

L2 Python contract tests - retry and reconnect logic

Covers:
- Retry on connection-related exceptions
- Return an error after reaching max retry attempts
- Stop retrying once an attempt succeeds
- Keep socket state correct across disconnect, reconnect, and retry flow
"""

import json
from unittest.mock import patch, MagicMock

import pytest

from unreal_mcp_server_advanced import UnrealConnection


def _payload(data: dict) -> bytes:
    return json.dumps(data).encode("utf-8")


class TestRetryOnConnectionErrors:
    def test_retry_on_socket_timeout(self, fake_socket_factory):
        conn = UnrealConnection()
        fail = fake_socket_factory(raise_on_connect=TimeoutError("timeout"))
        ok_payload = _payload({"success": True})
        ok = fake_socket_factory(response_payloads=[ok_payload])

        created = []

        def factory():
            fake = fail if len(created) == 0 else ok
            created.append(fake)
            return fake

        with patch.object(conn, "_create_socket", side_effect=factory), patch("time.sleep"):
            result = conn.send_command("spawn_actor", {})

        assert len(created) == 2
        assert result["success"] is True

    def test_retry_on_connection_refused(self, fake_socket_factory):
        conn = UnrealConnection()
        fail = fake_socket_factory(raise_on_connect=ConnectionRefusedError("refused"))
        ok_payload = _payload({"success": True})
        ok = fake_socket_factory(response_payloads=[ok_payload])

        created = []

        def factory():
            fake = fail if len(created) == 0 else ok
            created.append(fake)
            return fake

        with patch.object(conn, "_create_socket", side_effect=factory), patch("time.sleep"):
            result = conn.send_command("delete_actor", {"name": "X"})

        assert len(created) == 2
        assert result["success"] is True

    def test_retry_on_recv_empty(self, fake_socket_factory):
        conn = UnrealConnection()
        fail = fake_socket_factory(response_payloads=[], close_after_n_recv=1)
        ok_payload = _payload({"success": True})
        ok = fake_socket_factory(response_payloads=[ok_payload])

        created = []

        def factory():
            fake = fail if len(created) == 0 else ok
            created.append(fake)
            return fake

        with patch.object(conn, "_create_socket", side_effect=factory), patch("time.sleep"):
            result = conn.send_command("set_actor_transform", {"name": "X"})

        assert len(created) == 2
        assert result["success"] is True


class TestNoRetryOnUnexpectedErrors:
    def test_no_retry_on_runtime_error(self, fake_socket_factory):
        conn = UnrealConnection()
        fake = fake_socket_factory(response_payloads=[])

        def boom(*a, **k):
            raise RuntimeError("boom")

        with patch.object(conn, "_create_socket", return_value=fake), patch("time.sleep"):
            with patch.object(conn, "connect", side_effect=boom):
                result = conn.send_command("spawn_actor", {})

        assert result["success"] is False
        assert "boom" in result["error"]

    def test_no_retry_on_type_error(self, fake_socket_factory):
        conn = UnrealConnection()
        fake = fake_socket_factory(response_payloads=[])

        def kaboom(*a, **k):
            raise TypeError("bad type")

        with patch.object(conn, "_create_socket", return_value=fake), patch("time.sleep"):
            with patch.object(conn, "connect", side_effect=kaboom):
                result = conn.send_command("spawn_actor", {})

        assert result["success"] is False


class TestMaxRetriesExceeded:
    def test_all_attempts_fail_return_error(self, fake_socket_factory):
        conn = UnrealConnection()
        fail = fake_socket_factory(raise_on_connect=ConnectionRefusedError("nope"))
        with patch.object(conn, "_create_socket", return_value=fail), patch("time.sleep"):
            result = conn.send_command("spawn_actor", {})
        assert result["success"] is False
        assert "failed after" in result["error"].lower()

    def test_socket_closed_and_recreated_between_attempts(self, fake_socket_factory):
        conn = UnrealConnection()
        ok = fake_socket_factory(response_payloads=[])
        # connect() succeeds, but _receive_response raises ConnectionError every time -> send_command retries.
        def recv_error(*a, **k):
            raise ConnectionError("recv closed")
        with patch.object(conn, "_create_socket", return_value=ok) as mock_create, \
             patch("time.sleep"), \
             patch.object(conn, "_receive_response", side_effect=recv_error):
            conn.send_command("spawn_actor", {})
        # send_command tries MAX_RETRIES + 1 times, each attempt calling connect -> _create_socket.
        assert mock_create.call_count == conn.MAX_RETRIES + 1


class TestRetryWithExponentialBackoff:
    def test_delays_increase(self, fake_socket_factory):
        conn = UnrealConnection()
        ok = fake_socket_factory(response_payloads=[])
        slept = []

        def capture_sleep(d):
            slept.append(d)

        def recv_error(*a, **k):
            raise ConnectionError("recv closed")

        with patch.object(conn, "_create_socket", return_value=ok), \
             patch("time.sleep", side_effect=capture_sleep), \
             patch.object(conn, "_receive_response", side_effect=recv_error):
            conn.send_command("spawn_actor", {})

        # MAX_RETRIES = 3 -> send_command performs retry sleep 3 times.
        assert len(slept) == conn.MAX_RETRIES
        for i in range(1, len(slept)):
            assert slept[i] >= slept[i - 1] or pytest.approx(slept[i]) == conn.MAX_RETRY_DELAY