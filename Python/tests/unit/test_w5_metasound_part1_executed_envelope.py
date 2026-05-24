"""W5 executed-envelope tests for MetaSound handlers (issue #99)."""
from unittest.mock import patch, MagicMock
import pytest
import server.metasound_tools as m
from utils.envelope import assert_executed, assert_no_queued, EnvelopeAssertionError


def _conn_returning(payload):
    c = MagicMock()
    c.send_command.return_value = payload
    return c


def _executed_envelope(command, extra=None):
    data = {"executed": True, "command": command}
    if extra:
        data.update(extra)
    return {"success": True, "data": data}


METASOUND_COMMANDS = [
    ("edit_sound_cue_graph", lambda: m.edit_sound_cue_graph("/Game/Sounds/SC_Test", "USoundNodeMixer", "MixNode")),
    ("create_metasound_source", lambda: m.create_metasound_source("/Game/Audio", "MS_Test")),
    ("create_metasound_patch", lambda: m.create_metasound_patch("/Game/Audio", "MSP_Test")),
    ("add_metasound_graph_node", lambda: m.add_metasound_graph_node("/Game/Audio/MS_Test", "Trigger")),
    ("set_metasound_parameter", lambda: m.set_metasound_parameter("BP_Actor", "Volume", 0.5)),
    ("bind_footstep_audio", lambda: m.bind_footstep_audio("/Game/Anims/AS_Walk", "/Game/Sounds/SC_Footstep")),
    ("configure_ui_sound", lambda: m.configure_ui_sound("UW_MainMenu", "/Game/Sounds/SC_Click")),
]


@pytest.mark.parametrize("command,call", METASOUND_COMMANDS)
def test_metasound_promoted_handler_returns_executed_envelope(command, call):
    payload = _executed_envelope(command)
    conn = _conn_returning(payload)
    with patch("server.metasound_tools.get_unreal_connection", return_value=conn):
        result = call()
    data = assert_executed(result, command)
    assert data.get("command") == command


@pytest.mark.parametrize("command,call", METASOUND_COMMANDS)
def test_metasound_promoted_handler_rejects_queued_regression(command, call):
    queued = {"success": True, "data": {"command": command, "queued": True, "hint": "fallback"}}
    conn = _conn_returning(queued)
    with patch("server.metasound_tools.get_unreal_connection", return_value=conn):
        result = call()
    with pytest.raises(EnvelopeAssertionError, match="queued"):
        assert_executed(result, command)
