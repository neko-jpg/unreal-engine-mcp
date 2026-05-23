"""234-stubs W2 (#87): executed-envelope tests for Sequencer Extension (6 handlers).

This file pairs with the C++ promotion of all 6 handlers in
`EpicUnrealMCPSequencerExtensionCommands.cpp` from `queued: true` to the
canonical `{success:true, data:{executed:true, ...}}` envelope.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import server.sequencer_extension_tools as seq
from utils.envelope import EnvelopeAssertionError, assert_executed


def _conn_returning(payload):
    m = MagicMock()
    m.send_command.return_value = payload
    return m


def _executed_envelope(command, **extra):
    data = {"command": command, "executed": True}
    data.update(extra)
    return {"success": True, "data": data}


SEQUENCER_COMMANDS = [
    ("spawn_camera_rail", lambda: seq.spawn_camera_rail("CameraRail", [])),
    ("spawn_camera_crane", lambda: seq.spawn_camera_crane("CameraCrane", 300.0)),
    ("sequencer_render_preview", lambda: seq.sequencer_render_preview("/Game/Cinematics/LS_Hero")),
    ("register_take_recorder_source", lambda: seq.register_take_recorder_source("ActorRecorder", "BP_Hero")),
    ("add_control_rig_track", lambda: seq.add_control_rig_track("/Game/Cinematics/LS_Hero", "binding_01", "/Game/Rig/CR_Hero")),
    ("spawn_level_sequence_actor", lambda: seq.spawn_level_sequence_actor("/Game/Cinematics/LS_Hero", "LSA_Hero")),
]


@pytest.mark.parametrize("command,call", SEQUENCER_COMMANDS)
def test_sequencer_promoted_handler_returns_executed_envelope(command, call):
    payload = _executed_envelope(command, mcp_metadata_keys_persisted=2)
    conn = _conn_returning(payload)
    with patch("server.sequencer_extension_tools.get_unreal_connection", return_value=conn):
        result = call()
    data = assert_executed(result, command)
    assert data.get("command") == command


@pytest.mark.parametrize("command,call", SEQUENCER_COMMANDS)
def test_sequencer_promoted_handler_rejects_queued_regression(command, call):
    queued = {"success": True, "data": {"command": command, "queued": True, "hint": "fallback"}}
    conn = _conn_returning(queued)
    with patch("server.sequencer_extension_tools.get_unreal_connection", return_value=conn):
        result = call()
    with pytest.raises(EnvelopeAssertionError, match="queued"):
        assert_executed(result, command)
