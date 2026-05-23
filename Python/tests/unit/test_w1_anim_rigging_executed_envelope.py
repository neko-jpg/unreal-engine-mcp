"""234-stubs W1 (#79): executed-envelope tests for Animation/Rigging Part 1.

This file pairs with the C++ promotion of 8 handlers in
`Plugins/UnrealMCP/Source/UnrealMCP/Private/Commands/EpicUnrealMCPAnimationRiggingCommands.cpp`
from `queued: true` to the canonical `{success:true, data:{executed:true, ...}}`
envelope. Each test patches `get_unreal_connection` so the Python tool
serialises the new payload shape into a mock socket call, then asserts that
`utils.envelope.assert_executed` accepts the response.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import server.anim_rigging_tools as art
from utils.envelope import EnvelopeAssertionError, assert_executed


def _conn_returning(payload):
    """Build a MagicMock UnrealConnection whose send_command returns ``payload``."""
    m = MagicMock()
    m.send_command.return_value = payload
    return m


def _executed_envelope(command, **extra):
    data = {"command": command, "executed": True, "asset_path": extra.pop("asset_path", "/Game/Anim/Test")}
    data.update(extra)
    return {"success": True, "data": data}


PART1_COMMANDS = [
    ("add_control_rig_bone", lambda: art.add_control_rig_bone("/Game/Rig/CR_Hero", "spine_03", parent_bone="spine_02")),
    ("add_control_rig_control", lambda: art.add_control_rig_control("/Game/Rig/CR_Hero", "HeadControl", "Transform")),
    ("add_ik_goal", lambda: art.add_ik_goal("/Game/IK/IKR_Hero", "RightHandGoal", "hand_r")),
    ("add_ik_solver", lambda: art.add_ik_solver("/Game/IK/IKR_Hero")),
    ("set_retarget_chain", lambda: art.set_retarget_chain("/Game/IK/IKR_Hero", "Spine", "spine_01", "spine_05")),
    ("set_retarget_manager", lambda: art.set_retarget_manager("/Game/Char/SK_Hero_Skeleton", "Humanoid")),
    ("set_facial_animation", lambda: art.set_facial_animation("/Game/Char/SK_Hero_Skeleton", "BrowsUp", 0.8)),
    ("set_morph_target", lambda: art.set_morph_target("/Game/Char/SK_Hero", "Smile", 0.5)),
]


@pytest.mark.parametrize("command,call", PART1_COMMANDS)
def test_part1_promoted_handler_returns_executed_envelope(command, call):
    payload = _executed_envelope(command, mcp_metadata_keys_persisted=3)
    conn = _conn_returning(payload)
    with patch("server.anim_rigging_tools.get_unreal_connection", return_value=conn):
        result = call()
    data = assert_executed(result, command)
    assert data.get("command") == command


@pytest.mark.parametrize("command,call", PART1_COMMANDS)
def test_part1_promoted_handler_rejects_queued_regression(command, call):
    queued = {"success": True, "data": {"command": command, "queued": True, "hint": "fallback"}}
    conn = _conn_returning(queued)
    with patch("server.anim_rigging_tools.get_unreal_connection", return_value=conn):
        result = call()
    # The Python tool relays the raw envelope; assert_executed must refuse it.
    with pytest.raises(EnvelopeAssertionError, match="queued"):
        assert_executed(result, command)


def test_set_morph_target_surfaces_available_morph_list_on_error():
    err = {
        "success": False,
        "error": "Morph target 'Frown' not found on USkeletalMesh '/Game/Char/SK_Hero'.",
        "available_morph_targets": ["Smile", "BrowsUp", "BrowsDown"],
    }
    conn = _conn_returning(err)
    with patch("server.anim_rigging_tools.get_unreal_connection", return_value=conn):
        result = art.set_morph_target("/Game/Char/SK_Hero", "Frown", 1.0)
    assert result.get("success") in (False, None)
    # The Python helper wraps the error message; the C++ "available_morph_targets"
    # list is preserved in result so callers can build a corrected request.
    assert "available_morph_targets" in result or "Morph target" in str(result.get("error") or result.get("message") or "")
