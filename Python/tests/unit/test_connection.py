"""
tests/unit/test_connection.py

L1 Python unit tests - UnrealConnection core behavior

Covers:
- connect() / disconnect()
- send_command() retry behavior
- _get_timeout_for_command()
- _send_command_once() payload shape
- Global connection management (get_unreal_connection / reset_unreal_connection)
- Error paths: socket timeout, connection refused, recv disconnect, JSON decode error, retry limit

All tests run without a real Unreal instance using FakeSocket and monkeypatch.
"""

import json
import socket
import threading
import time
from unittest.mock import patch

import pytest

import unreal_mcp_server_advanced as srv
from unreal_mcp_server_advanced import UnrealConnection, get_unreal_connection, reset_unreal_connection


# ---------------------------------------------------------------------------
# connect()
# ---------------------------------------------------------------------------

class TestConnect:
    def test_connect_success_returns_true(self, fake_socket_factory):
        conn = UnrealConnection()
        fake = fake_socket_factory()
        with patch.object(conn, "_create_socket", return_value=fake):
            result = conn.connect()
        assert result is True
        assert conn.connected is True

    def test_connect_failure_retries_up_to_max(self, fake_socket_factory):
        conn = UnrealConnection()
        fake = fake_socket_factory(raise_on_connect=ConnectionRefusedError("nope"))
        with patch.object(conn, "_create_socket", return_value=fake):
            start = time.time()
            result = conn.connect()
            elapsed = time.time() - start
        assert result is False
        assert conn.connected is False
        # Retries MAX_RETRIES times -> first attempt + 3 retries = 4 total.
        assert fake._recv_count == 0  # recv is never called.
        # Exponential backoff: 0.5 + 1.0 + 2.0 = 3.5s minimum.
        assert elapsed >= 3.0

    def test_connect_exponential_backoff_delays(self, fake_socket_factory):
        conn = UnrealConnection()
        fake = fake_socket_factory(raise_on_connect=ConnectionRefusedError("nope"))
        delays = []
        orig_sleep = time.sleep

        def capture_sleep(d):
            delays.append(d)
            orig_sleep(d)

        with patch.object(conn, "_create_socket", return_value=fake), patch("time.sleep", side_effect=capture_sleep):
            conn.connect()

        # attempts 0->1: delay 0.5, 1->2: 1.0, 2->3: 2.0
        assert pytest.approx(delays[0], abs=0.05) == 0.5
        assert pytest.approx(delays[1], abs=0.05) == 1.0
        assert pytest.approx(delays[2], abs=0.05) == 2.0

    def test_connect_respects_max_retry_delay(self):
        conn = UnrealConnection()
        conn.BASE_RETRY_DELAY = 10.0
        fake_closes = []
        for _ in range(conn.MAX_RETRIES + 1):
            fake_closes.append(socket.timeout("conn timeout"))

        call_count = 0

        def make_sock():
            nonlocal call_count
            call_count += 1
            return fake_socket_factory(raise_on_connect=socket.timeout("timeout"))

        with patch.object(conn, "_create_socket", side_effect=make_sock), patch("time.sleep") as mock_sleep:
            conn.connect()

        # Delays are capped at MAX_RETRY_DELAY = 5.0.
        for call in mock_sleep.call_args_list:
            assert call[0][0] <= conn.MAX_RETRY_DELAY


# ---------------------------------------------------------------------------
# disconnect()
# ---------------------------------------------------------------------------

class TestDisconnect:
    def test_disconnect_closes_socket_and_resets_state(self, fake_socket_factory):
        conn = UnrealConnection()
        fake = fake_socket_factory()
        with patch.object(conn, "_create_socket", return_value=fake):
            conn.connect()
        assert conn.socket is not None
        conn.disconnect()
        assert conn.socket is None
        assert conn.connected is False


# ---------------------------------------------------------------------------
# _get_timeout_for_command()
# ---------------------------------------------------------------------------

class TestGetTimeoutForCommand:
    def test_large_operation_commands_return_long_timeout(self):
        conn = UnrealConnection()
        assert conn._get_timeout_for_command("create_town") == conn.LARGE_OP_RECV_TIMEOUT
        assert conn._get_timeout_for_command("create_castle_fortress") == conn.LARGE_OP_RECV_TIMEOUT
        assert conn._get_timeout_for_command("get_available_materials") == conn.LARGE_OP_RECV_TIMEOUT

    def test_normal_commands_return_default_timeout(self):
        conn = UnrealConnection()
        assert conn._get_timeout_for_command("spawn_actor") == conn.DEFAULT_RECV_TIMEOUT
        assert conn._get_timeout_for_command("delete_actor") == conn.DEFAULT_RECV_TIMEOUT


# ---------------------------------------------------------------------------
# send_command() retry
# ---------------------------------------------------------------------------

class TestSendCommandRetry:
    def test_send_command_retries_on_connection_error(self, fake_socket_factory):
        conn = UnrealConnection()
        # First attempt disconnects on recv, second attempt succeeds.
        fail = fake_socket_factory(response_payloads=[], close_after_n_recv=1)
        success_payload = json.dumps({"status": "success", "result": {"name": "A"}}).encode("utf-8")
        ok = fake_socket_factory(response_payloads=[success_payload])

        created = []

        def side():
            fake = fail if len(created) == 0 else ok
            created.append(fake)
            return fake

        with patch.object(conn, "_create_socket", side_effect=side), patch("time.sleep"):
            response = conn.send_command("spawn_actor", {"name": "A"})
        assert response["status"] == "success"
        assert len(created) == 2

    def test_send_command_does_not_retry_on_unexpected_exception(self, fake_socket_factory):
        conn = UnrealConnection()
        fake = fake_socket_factory(response_payloads=[])

        def boom(*args, **kwargs):
            raise RuntimeError("boom")

        with patch.object(conn, "_create_socket", return_value=fake):
            with patch.object(conn, "connect", side_effect=boom):
                response = conn.send_command("spawn_actor", {})
        assert response["status"] == "error"
        assert "boom" in response.get("error", "")

    def test_send_command_returns_error_after_max_retries(self, fake_socket_factory):
        conn = UnrealConnection()
        fail = fake_socket_factory(raise_on_connect=ConnectionRefusedError("refused"))
        with patch.object(conn, "_create_socket", return_value=fail), patch("time.sleep"):
            response = conn.send_command("spawn_actor", {})
        assert response["status"] == "error"
        assert "failed after" in response.get("error", "").lower()


# ---------------------------------------------------------------------------
# _send_command_once()
# ---------------------------------------------------------------------------

class TestSendCommandOnce:
    def test_payload_contains_type_and_params(self, fake_socket_factory):
        conn = UnrealConnection()
        payload = json.dumps({"status": "success", "result": {}}).encode("utf-8")
        fake = fake_socket_factory(response_payloads=[payload])
        with patch.object(conn, "_create_socket", return_value=fake):
            conn._send_command_once("my_cmd", {"key": 42}, 0)
        sent = json.loads(fake._last_sent.decode("utf-8"))
        assert sent["type"] == "my_cmd"
        assert sent["params"] == {"key": 42}

    def test_payload_with_none_params_defaults_to_empty_dict(self, fake_socket_factory):
        conn = UnrealConnection()
        payload = json.dumps({"status": "success", "result": {}}).encode("utf-8")
        fake = fake_socket_factory(response_payloads=[payload])
        with patch.object(conn, "_create_socket", return_value=fake):
            conn._send_command_once("my_cmd", None, 0)
        sent = json.loads(fake._last_sent.decode("utf-8"))
        assert sent["params"] == {}

    def test_error_response_returned_as_is(self, fake_socket_factory):
        conn = UnrealConnection()
        payload = json.dumps({"status": "error", "error": "not found"}).encode("utf-8")
        fake = fake_socket_factory(response_payloads=[payload])
        with patch.object(conn, "_create_socket", return_value=fake):
            resp = conn._send_command_once("my_cmd", {}, 0)
        assert resp["status"] == "error"
        assert resp["error"] == "not found"

    def test_legacy_success_false_normalized_to_error(self, fake_socket_factory):
        conn = UnrealConnection()
        payload = json.dumps({"success": False, "error": "legacy fail"}).encode("utf-8")
        fake = fake_socket_factory(response_payloads=[payload])
        with patch.object(conn, "_create_socket", return_value=fake):
            resp = conn._send_command_once("my_cmd", {}, 0)
        assert resp["status"] == "error"
        assert resp["error"] == "legacy fail"


# ---------------------------------------------------------------------------
# Global connection management
# ---------------------------------------------------------------------------

class TestGlobalConnection:
    def test_get_unreal_connection_returns_same_instance(self):
        a = get_unreal_connection()
        b = get_unreal_connection()
        assert a is b
        assert isinstance(a, UnrealConnection)

    def test_get_unreal_connection_lazy_initialization(self):
        assert srv._unreal_connection is None
        c = get_unreal_connection()
        assert srv._unreal_connection is c

    def test_singleton_thread_safe(self):
        results = []

        def fetch():
            results.append(get_unreal_connection())

        threads = [threading.Thread(target=fetch) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        first = results[0]
        assert all(r is first for r in results)

    def test_reset_unreal_connection_clears_singleton(self):
        c = get_unreal_connection()
        assert srv._unreal_connection is not None
        reset_unreal_connection()
        assert srv._unreal_connection is None

    def test_reset_unreal_connection_disconnects_existing(self):
        c = get_unreal_connection()
        with patch.object(c, "disconnect") as mock_dc:
            reset_unreal_connection()
        mock_dc.assert_called_once()

# ---------------------------------------------------------------------------
# Error-path coverage
# ---------------------------------------------------------------------------

class TestSendCommandErrors:
    def test_socket_timeout_on_connect(self, fake_socket_factory):
        conn = UnrealConnection()
        fake = fake_socket_factory(raise_on_connect=socket.timeout("timed out"))
        with patch.object(conn, "_create_socket", return_value=fake), patch("time.sleep"):
            response = conn.send_command("spawn_actor", {})
        assert response["status"] == "error"
        assert "timed out" in response["error"].lower() or "timeout" in response["error"].lower()

    def test_os_error_on_connect(self, fake_socket_factory):
        conn = UnrealConnection()
        fake = fake_socket_factory(raise_on_connect=OSError("bad file descriptor"))
        with patch.object(conn, "_create_socket", return_value=fake), patch("time.sleep"):
            response = conn.send_command("spawn_actor", {})
        assert response["status"] == "error"

    def test_json_decode_error(self, fake_socket_factory):
        conn = UnrealConnection()
        bad = b'{"incomplete"'
        # Payload arrives once -> _receive_response tries JSON, fails, continues,
        # then next recv is empty -> ConnectionError with incomplete data.
        # _send_command_once surfaces that _receive_response exception.
        fake = fake_socket_factory(response_payloads=[bad])
        with patch.object(conn, "_create_socket", return_value=fake):
            with pytest.raises(ConnectionError):
                conn._send_command_once("cmd", {}, 0)

    def test_empty_response(self, fake_socket_factory):
        conn = UnrealConnection()
        fake = fake_socket_factory(response_payloads=[b""])
        with patch.object(conn, "_create_socket", return_value=fake):
            with pytest.raises((ConnectionError, json.JSONDecodeError)):
                conn._send_command_once("cmd", {}, 0)
