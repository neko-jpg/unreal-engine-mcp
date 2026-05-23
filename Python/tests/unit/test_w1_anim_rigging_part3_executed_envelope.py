"""234-stubs W1 (#79): executed-envelope tests for Animation/Rigging Part 3.

Closes #79 in tandem with the C++ promotion of the last 4 handlers in
`Plugins/UnrealMCP/Source/UnrealMCP/Private/Commands/EpicUnrealMCPAnimationRiggingCommands.cpp`.
After this PR every handler in the Animation Rigging category returns
`executed: true`; only the helper definitions of `AnimQueued` / `AnimOk`
keep the `queued: true` literal in source so the wave-close PR can drop
the baseline.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import server.anim_rigging_tools as art
from utils.envelope import EnvelopeAssertionError, assert_executed


def _conn(payload):
    m = MagicMock()
    m.send_command.return_value = payload
    return m


def _executed(command, **extra):
    data = {"command": command, "executed": True}
    data.update(extra)
    return {"success": True, "data": data}


PART3_COMMANDS = [
    ("create_aim_offset",
     lambda: art.create_aim_offset(skeleton_path="/Game/Char/SK_Hero_Skeleton")),
    ("create_control_rig",
     lambda: art.create_control_rig(skeleton_path="/Game/Char/SK_Hero_Skeleton", skeletal_mesh_path="/Game/Char/SK_Hero")),
    ("sequencer_control_rig_track",
     lambda: art.sequencer_control_rig_track("/Game/Cine/LS_Hero", control_rig_path="/Game/Rig/CR_Hero", track_name="HeroRig")),
    ("connect_metahuman",
     lambda: art.connect_metahuman(host_asset_path="/Game/Char/SK_Hero_Skeleton", metahuman_id="hero_v1", face_archetype="MetaHuman")),
]


@pytest.mark.parametrize("command,call", PART3_COMMANDS)
def test_part3_promoted_handler_returns_executed_envelope(command, call):
    conn = _conn(_executed(command, asset_path="/Game/X/Y", mode="metadata_fallback", mcp_metadata_keys_persisted=4))
    with patch("server.anim_rigging_tools.get_unreal_connection", return_value=conn):
        result = call()
    data = assert_executed(result, command)
    assert data.get("command") == command


@pytest.mark.parametrize("command,call", PART3_COMMANDS)
def test_part3_promoted_handler_rejects_queued_regression(command, call):
    queued = {"success": True, "data": {"command": command, "queued": True, "hint": "fallback"}}
    conn = _conn(queued)
    with patch("server.anim_rigging_tools.get_unreal_connection", return_value=conn):
        result = call()
    with pytest.raises(EnvelopeAssertionError, match="queued"):
        assert_executed(result, command)


def test_create_aim_offset_factory_mode_executed():
    payload = _executed("create_aim_offset", asset_path="/Game/Anim/AO_Hero", asset_name="AO_Hero", mode="factory")
    conn = _conn(payload)
    with patch("server.anim_rigging_tools.get_unreal_connection", return_value=conn):
        result = art.create_aim_offset(asset_name="AO_Hero", skeleton_path="/Game/Char/SK_Hero_Skeleton")
    data = assert_executed(result, "create_aim_offset")
    assert data.get("mode") == "factory"


def test_create_control_rig_metadata_fallback_executed():
    payload = _executed("create_control_rig",
                       host_asset_path="/Game/Char/SK_Hero_Skeleton",
                       wanted_class="/Script/ControlRigDeveloper.ControlRigBlueprint",
                       wanted_asset_name="CR_Hero",
                       wanted_package_path="/Game/Rig",
                       factory_unavailable_reason="ControlRigEditor module not loaded",
                       mode="metadata_fallback")
    conn = _conn(payload)
    with patch("server.anim_rigging_tools.get_unreal_connection", return_value=conn):
        result = art.create_control_rig(asset_path="/Game/Rig", asset_name="CR_Hero", skeleton_path="/Game/Char/SK_Hero_Skeleton")
    data = assert_executed(result, "create_control_rig")
    assert data.get("mode") == "metadata_fallback"
    assert data.get("host_asset_path") == "/Game/Char/SK_Hero_Skeleton"


def test_connect_metahuman_legacy_positional_call_works():
    """Legacy callers passing (metahuman_blueprint_path, target_actor=...) must keep working."""
    conn = _conn(_executed("connect_metahuman"))
    with patch("server.anim_rigging_tools.get_unreal_connection", return_value=conn):
        result = art.connect_metahuman("/Game/MH_BP", target_actor="MyMetahuman")
    args, _ = conn.send_command.call_args
    assert args[0] == "connect_metahuman"
    payload = args[1]
    assert payload["host_asset_path"] == "MyMetahuman"
    assert payload["metahuman_id"] == "/Game/MH_BP"
    assert payload["metahuman_blueprint_path"] == "/Game/MH_BP"
    assert payload["target_actor"] == "MyMetahuman"


def test_sequencer_control_rig_track_validates_level_sequence_path():
    conn = _conn(_executed("sequencer_control_rig_track"))
    with patch("server.anim_rigging_tools.get_unreal_connection", return_value=conn):
        result = art.sequencer_control_rig_track("")  # empty path must fail validation
    assert result.get("success") in (False, None)
    conn.send_command.assert_not_called()
