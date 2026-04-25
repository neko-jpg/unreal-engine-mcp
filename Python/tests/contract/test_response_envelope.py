"""
tests/contract/test_response_envelope.py

L2 Python contract tests - response envelope normalization

Covers:
- Correct handling of normalized {"success": True, ...data...}
- Correct handling of normalized {"success": False, "error": "..."}
- Helper layer can reach required data in normalized format
- Legacy format with success:false is normalized to an error response
- Unknown command can return an error envelope
"""

import json
from unittest.mock import patch

import pytest

import helpers.actor_name_manager as anm
import helpers.blueprint_graph.node_manager as nm
import helpers.blueprint_graph.variable_manager as vm
from tests.conftest import FakeUnrealConnection


class TestResponseEnvelopeHandling:
    def test_success_envelope_returned_as_is(self):
        conn = FakeUnrealConnection()
        conn.responses["spawn_actor"] = {"success": True, "name": "Hero"}
        result = conn.send_command("spawn_actor", {})
        assert result["success"] is True
        assert result["name"] == "Hero"

    def test_error_envelope_preserved(self):
        conn = FakeUnrealConnection()
        conn.responses["delete_actor"] = {"success": False, "error": "not found"}
        result = conn.send_command("delete_actor", {"name": "Hero"})
        assert result["success"] is False
        assert result["error"] == "not found"

    def test_legacy_success_false_normalized(self):
        conn = FakeUnrealConnection()
        # Normalization happens in UnrealConnection._send_command_once,
        # but FakeUnrealConnection does not do it, so validate helper-side acceptance.
        conn.responses["cmd"] = {"success": False, "error": "legacy fail"}
        result = conn.send_command("cmd", {})
        # FakeUnrealConnection returns as-is; normalization is verified in patched real-connection tests.
        assert result["success"] is False


class TestStatusErrorNormalizationInSendCommandOnce:
    """
    Direct tests for envelope normalization logic in UnrealConnection._send_command_once().
    """

    def test_legacy_success_false_becomes_error(self, fake_socket_factory):
        from unreal_mcp_server_advanced import UnrealConnection
        conn = UnrealConnection()
        payload = json.dumps({"success": False, "error": "some error", "message": "detailed"}).encode("utf-8")
        fake = fake_socket_factory(response_payloads=[payload])
        with patch.object(conn, "_create_socket", return_value=fake):
            resp = conn._send_command_once("cmd", {}, 0)
        assert resp["success"] is False
        assert resp["error"] == "some error"

    def test_message_fallback_when_error_missing(self, fake_socket_factory):
        from unreal_mcp_server_advanced import UnrealConnection
        conn = UnrealConnection()
        payload = json.dumps({"success": False, "message": "msg only"}).encode("utf-8")
        fake = fake_socket_factory(response_payloads=[payload])
        with patch.object(conn, "_create_socket", return_value=fake):
            resp = conn._send_command_once("cmd", {}, 0)
        assert resp["success"] is False
        assert resp["error"] == "msg only"

    def test_unknown_error_fallback(self, fake_socket_factory):
        from unreal_mcp_server_advanced import UnrealConnection
        conn = UnrealConnection()
        payload = json.dumps({"status": "error"}).encode("utf-8")
        fake = fake_socket_factory(response_payloads=[payload])
        with patch.object(conn, "_create_socket", return_value=fake):
            resp = conn._send_command_once("cmd", {}, 0)
        assert resp["success"] is False
        assert resp["error"] == "Unknown error"

    def test_success_with_result_flattened(self, fake_socket_factory):
        from unreal_mcp_server_advanced import UnrealConnection
        conn = UnrealConnection()
        payload = json.dumps({"status": "success", "result": {"name": "Hero", "id": 42}}).encode("utf-8")
        fake = fake_socket_factory(response_payloads=[payload])
        with patch.object(conn, "_create_socket", return_value=fake):
            resp = conn._send_command_once("spawn_actor", {}, 0)
        assert resp["success"] is True
        assert resp["name"] == "Hero"
        assert resp["id"] == 42
        assert "result" not in resp


class TestHelperLayerEnvelopeIndependence:
    """
    Verify the helper layer works independently of envelope style.
    """

    def test_node_manager_extracts_node_id(self):
        conn = FakeUnrealConnection()
        conn.responses["add_blueprint_node"] = {"success": True, "node_id": "N1"}
        result = nm.add_node(conn, "BP", "Print", {"message": "hi"})
        assert result["success"] is True
        assert result["node_id"] == "N1"

    def test_variable_manager_extracts_variable(self):
        conn = FakeUnrealConnection()
        conn.responses["create_variable"] = {"success": True, "name": "Health"}
        result = vm.create_variable(conn, "BP", "Health", "float")
        assert result["success"] is True

    def test_safe_spawn_actor_envelope_independence(self):
        conn = FakeUnrealConnection()
        conn.responses["spawn_actor"] = {"success": True, "name": "Hero"}
        anm.clear_actor_cache()
        result = anm.safe_spawn_actor(conn, {"name": "Hero"})
        assert result["success"] is True
        assert result["final_name"] == "Hero"


class TestUnknownCommandErrorEnvelope:
    """
    Check error envelope behavior when Unreal returns an unknown command error.
    At implementation level UnrealConnection only sends commands,
    so this validates the response shape received by Python.
    """

    def test_unknown_command_returns_error_from_fake(self):
        conn = FakeUnrealConnection()
        conn.responses["unknown_cmd"] = {"success": False, "error": "Unknown command: unknown_cmd"}
        result = conn.send_command("unknown_cmd", {})
        assert result["success"] is False
        assert "unknown" in result["error"].lower()