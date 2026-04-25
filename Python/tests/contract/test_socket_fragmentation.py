"""
tests/contract/test_socket_fragmentation.py

L2 Python contract/protocol tests - resilience to fragmented socket responses

Covers:
- A single send_command() sends one command JSON payload
- Responses split across multiple recv() calls are fully reassembled
- Responses larger than 8KB are correctly joined
- Incomplete JSON is never treated as success
- Disconnects transition into reconnect logic
- Long JSON and large graph-analysis responses remain stable
"""

import json
from unittest.mock import patch

import pytest

from unreal_mcp_server_advanced import UnrealConnection


def _payload(data: dict) -> bytes:
    return (json.dumps(data) + "\n").encode("utf-8")


class TestSingleCommandPerSend:
    def test_one_json_object_per_send(self, fake_socket_factory):
        conn = UnrealConnection()
        resp = _payload({"success": True})
        fake = fake_socket_factory(response_payloads=[resp])
        with patch.object(conn, "_create_socket", return_value=fake):
            conn._send_command_once("my_command", {"key": "val"}, 0)
        sent = json.loads(fake._last_sent.decode("utf-8"))
        # Single JSON root object.
        assert isinstance(sent, dict)
        assert sent["command"] == "my_command"


class TestMultiChunkReassembly:
    def test_small_chunks_across_many_recv(self, fake_socket_factory):
        conn = UnrealConnection()
        big = {"success": True, "nodes": list(range(2000))}
        payload = _payload(big)
        # 32 bytes per chunk.
        fake = fake_socket_factory(response_payloads=[payload], chunk_size=32)
        with patch.object(conn, "_create_socket", return_value=fake):
            conn.connect()
        raw = conn._receive_response("analyze_blueprint_graph")
        parsed = json.loads(raw.decode("utf-8"))
        assert parsed["success"] is True or parsed.get("status") == "success"

    def test_8kb_boundary_crossing(self, fake_socket_factory):
        conn = UnrealConnection()
        # Response larger than BUFFER_SIZE = 8192.
        big = {"success": True, "data": "X" * 10000}
        payload = _payload(big)
        fake = fake_socket_factory(response_payloads=[payload], chunk_size=4096)
        with patch.object(conn, "_create_socket", return_value=fake):
            conn.connect()
        raw = conn._receive_response("get_available_materials")
        parsed = json.loads(raw.decode("utf-8"))
        assert len(parsed["data"]) == 10000

    def test_large_graph_response(self, fake_socket_factory):
        conn = UnrealConnection()
        nodes = [{"id": i, "type": "Print", "pos_x": i * 10, "pos_y": i * 20} for i in range(500)]
        payload = _payload({"success": True, "graph_name": "EventGraph", "nodes": nodes})
        fake = fake_socket_factory(response_payloads=[payload], chunk_size=1024)
        with patch.object(conn, "_create_socket", return_value=fake):
            conn.connect()
        raw = conn._receive_response("analyze_blueprint_graph")
        parsed = json.loads(raw.decode("utf-8"))
        assert len(parsed["nodes"]) == 500


class TestIncompleteJsonDoesNotSucceed:
    def test_partial_json_raises(self, fake_socket_factory):
        conn = UnrealConnection()
        partial = b'{"success": true, "a": 1'
        fake = fake_socket_factory(response_payloads=[partial], chunk_size=8, close_after_n_recv=1)
        with patch.object(conn, "_create_socket", return_value=fake):
            conn.connect()
        with pytest.raises(ConnectionError):
            conn._receive_response("spawn_actor")

    def test_truncated_after_valid_prefix_raises(self, fake_socket_factory):
        conn = UnrealConnection()
        partial = b'{"success": true, '
        fake = fake_socket_factory(response_payloads=[partial], chunk_size=8, close_after_n_recv=1)
        with patch.object(conn, "_create_socket", return_value=fake):
            conn.connect()
        with pytest.raises(ConnectionError):
            conn._receive_response("spawn_actor")

    def test_empty_response_raises(self, fake_socket_factory):
        conn = UnrealConnection()
        fake = fake_socket_factory(response_payloads=[])
        with patch.object(conn, "_create_socket", return_value=fake):
            conn.connect()
        with pytest.raises(ConnectionError):
            conn._receive_response("spawn_actor")


class TestDisconnectTriggersReconnect:
    def test_send_command_reconnects_on_connection_error(self, fake_socket_factory):
        conn = UnrealConnection()
        # First attempt disconnects immediately, second succeeds.
        fail = fake_socket_factory(response_payloads=[], close_after_n_recv=1)
        ok_payload = _payload({"success": True, "id": 1})
        ok = fake_socket_factory(response_payloads=[ok_payload])

        created = []

        def factory():
            fake = fail if len(created) == 0 else ok
            created.append(fake)
            return fake

        with patch.object(conn, "_create_socket", side_effect=factory), patch("time.sleep"):
            result = conn.send_command("spawn_actor", {"name": "A"})

        assert result["success"] is True
        # Retry created a second socket instance.
        assert len(created) == 2

    def test_send_command_retried_on_os_error(self, fake_socket_factory):
        conn = UnrealConnection()
        fail = fake_socket_factory(raise_on_connect=OSError("Network is unreachable"))
        ok_payload = _payload({"success": True})
        ok = fake_socket_factory(response_payloads=[ok_payload])

        created = []

        def factory():
            fake = fail if len(created) == 0 else ok
            created.append(fake)
            return fake

        with patch.object(conn, "_create_socket", side_effect=factory), patch("time.sleep"):
            result = conn.send_command("get_actors_in_level", {})

        # OSError is a connection-related error and should be retried.
        assert len(created) == 2
        assert result["success"] is True

    def test_disconnect_triggers_no_retry_on_unexpected_error(self, fake_socket_factory):
        """
        Non-connection exceptions like JSON decode errors are not retried.
        """
        conn = UnrealConnection()
        # Non-JSON payload: json.loads raises ValueError, which is not retryable.
        bad = b'not json'
        fake = fake_socket_factory(response_payloads=[bad])
        with patch.object(conn, "_create_socket", return_value=fake):
            result = conn.send_command("spawn_actor", {})
        assert result["success"] is False
        # Because ValueError is not retried, failure happens on first handling path.
        assert "failed" in result["error"].lower() or "json" in result["error"].lower()


class TestPacketIndependence:
    """
    Verify behavior is independent of message/packet split boundaries.
    """

    def test_varied_chunk_sizes_produce_same_result(self, fake_socket_factory):
        conn = UnrealConnection()
        data = {"success": True, "message": "Hello world", "count": 42}
        payload = _payload(data)
        for chunk_size in [1, 7, 64, 1024, 8192, 16384]:
            fake = fake_socket_factory(response_payloads=[payload], chunk_size=chunk_size)
            with patch.object(conn, "_create_socket", return_value=fake):
                conn.connect()
            raw = conn._receive_response("spawn_actor")
            parsed = json.loads(raw.decode("utf-8"))
            assert parsed == data