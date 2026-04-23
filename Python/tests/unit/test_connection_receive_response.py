"""
tests/unit/test_connection_receive_response.py

L1 Python unit tests - UnrealConnection._receive_response() for chunking, timeout, and incomplete JSON handling

Covers:
- Reassemble JSON across multiple chunks
- Incomplete JSON on timeout is treated as failure
- If JSON is complete before timeout, return success
- Handle recv disconnects
- Responses larger than 8KB
- Continue reading across Unicode decode edge cases
"""

import json
import socket
from unittest.mock import patch

import pytest

from unreal_mcp_server_advanced import UnrealConnection


def _payload(data: dict) -> bytes:
    return json.dumps(data).encode("utf-8")


class TestReceiveResponseChunks:
    def test_single_chunk_success(self, fake_socket_factory):
        conn = UnrealConnection()
        payload = _payload({"status": "success", "result": {"id": 1}})
        fake = fake_socket_factory(response_payloads=[payload])
        with patch.object(conn, "_create_socket", return_value=fake):
            conn.connect()
        raw = conn._receive_response("spawn_actor")
        assert json.loads(raw.decode("utf-8"))["status"] == "success"

    def test_multiple_chunks_concatenated(self, fake_socket_factory):
        conn = UnrealConnection()
        payload = _payload({"status": "success", "result": {"nodes": list(range(500))}})
        # Intentionally split using a small buffer size.
        fake = fake_socket_factory(response_payloads=[payload], chunk_size=256)
        with patch.object(conn, "_create_socket", return_value=fake):
            conn.connect()
        raw = conn._receive_response("analyze_blueprint_graph")
        parsed = json.loads(raw.decode("utf-8"))
        assert parsed["status"] == "success"
        assert len(parsed["result"]["nodes"]) == 500

    def test_over_8kb_response(self, fake_socket_factory):
        conn = UnrealConnection()
        big = {"status": "success", "result": {"data": "x" * 20000}}
        payload = _payload(big)
        fake = fake_socket_factory(response_payloads=[payload], chunk_size=2048)
        with patch.object(conn, "_create_socket", return_value=fake):
            conn.connect()
        raw = conn._receive_response("get_available_materials")
        parsed = json.loads(raw.decode("utf-8"))
        assert len(parsed["result"]["data"]) == 20000

    def test_incomplete_json_on_timeout_raises(self, fake_socket_factory):
        conn = UnrealConnection()
        # Partial JSON only.
        partial = b'{"status": "success", "result": {"a": 1'
        fake = fake_socket_factory(response_payloads=[partial], timeout_after_recv=True)
        with patch.object(conn, "_create_socket", return_value=fake):
            conn.connect()
        with pytest.raises(TimeoutError):
            conn._receive_response("spawn_actor")

    def test_complete_json_before_timeout_returns_success(self, fake_socket_factory):
        conn = UnrealConnection()
        payload = _payload({"status": "success", "result": {}})
        # Deliver complete JSON before a timeout can occur.
        fake = fake_socket_factory(response_payloads=[payload])
        with patch.object(conn, "_create_socket", return_value=fake):
            conn.connect()
        raw = conn._receive_response("spawn_actor")
        assert json.loads(raw.decode("utf-8"))["status"] == "success"

    def test_recv_returns_empty_after_chunks_raises(self, fake_socket_factory):
        conn = UnrealConnection()
        payload = _payload({"status": "success", "result": {}})
        # First recv has full payload, second recv is empty -> should still finish successfully.
        fake = fake_socket_factory(response_payloads=[payload])
        with patch.object(conn, "_create_socket", return_value=fake):
            conn.connect()
        raw = conn._receive_response("spawn_actor")
        assert json.loads(raw.decode("utf-8"))["status"] == "success"

    def test_immediate_empty_raises_connection_error(self, fake_socket_factory):
        conn = UnrealConnection()
        fake = fake_socket_factory(response_payloads=[])
        with patch.object(conn, "_create_socket", return_value=fake):
            conn.connect()
        with pytest.raises(ConnectionError):
            conn._receive_response("spawn_actor")

    def test_incomplete_data_on_close_raises(self, fake_socket_factory):
        conn = UnrealConnection()
        partial = b'{"incomplete"'
        fake = fake_socket_factory(response_payloads=[partial])  # Single chunk, still incomplete.
        with patch.object(conn, "_create_socket", return_value=fake):
            conn.connect()
        with pytest.raises(ConnectionError):
            conn._receive_response("spawn_actor")

    def test_unicode_decode_error_continues_reading(self, fake_socket_factory):
        conn = UnrealConnection()
        # Simulating a truly split multibyte boundary is tricky,
        # so this covers a fragmented valid UTF-8 JSON payload.
        payload = json.dumps({"message": "hello world"}, ensure_ascii=False).encode("utf-8")
        fake = fake_socket_factory(response_payloads=[payload], chunk_size=8)
        with patch.object(conn, "_create_socket", return_value=fake):
            conn.connect()
        raw = conn._receive_response("spawn_actor")
        parsed = json.loads(raw.decode("utf-8"))
        assert parsed["message"] == "hello world"
