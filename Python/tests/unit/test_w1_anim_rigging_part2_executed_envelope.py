"""234-stubs W1 (#79): executed-envelope tests for Animation/Rigging Part 2.

Pairs with the C++ promotion of 8 more handlers in
`Plugins/UnrealMCP/Source/UnrealMCP/Private/Commands/EpicUnrealMCPAnimationRiggingCommands.cpp`
from `queued: true` to the canonical executed envelope. Six handlers go
through the AnimMetaPersist helper (UAnimBlueprint / UAnimSequence /
UControlRigBlueprint metadata) while `create_ik_rig` and
`create_ik_retargeter` are two-tier: a runtime-resolved factory when the
IKRigEditor module is loaded, otherwise an AnimMetaFallback on the host
mesh / target rig.
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
    data = {
        "command": command,
        "executed": True,
        "asset_path": extra.pop("asset_path", "/Game/AB_Test"),
    }
    data.update(extra)
    return {"success": True, "data": data}


PART2_COMMANDS = [
    ("add_anim_graph_node", lambda: art.add_anim_graph_node("/Game/AB_Hero", "BlendListByBool", 100.0, 50.0)),
    ("create_anim_state_machine", lambda: art.create_anim_state_machine("/Game/AB_Hero", graph_name="Locomotion")),
    ("add_anim_state", lambda: art.add_anim_state("/Game/AB_Hero", "Locomotion", "Idle", anim_sequence_path="/Game/Anim/A_Idle")),
    ("create_anim_transition_rule", lambda: art.create_anim_transition_rule("/Game/AB_Hero", "Idle", "Run", condition="Speed > 100")),
    ("add_notify_state", lambda: art.add_notify_state("/Game/Anim/A_Run", "AnimNotifyState_Trail", 0.2, 0.8, track="DefaultTrack")),
    ("set_control_rig_constraint", lambda: art.set_control_rig_constraint("/Game/Rig/CR_Hero", "HeadControl", "Parent", target="spine_03")),
]


@pytest.mark.parametrize("command,call", PART2_COMMANDS)
def test_part2_promoted_handler_returns_executed_envelope(command, call):
    conn = _conn(_executed(command, mcp_metadata_keys_persisted=3))
    with patch("server.anim_rigging_tools.get_unreal_connection", return_value=conn):
        result = call()
    data = assert_executed(result, command)
    assert data.get("command") == command


@pytest.mark.parametrize("command,call", PART2_COMMANDS)
def test_part2_promoted_handler_rejects_queued_regression(command, call):
    queued = {"success": True, "data": {"command": command, "queued": True, "hint": "fallback"}}
    conn = _conn(queued)
    with patch("server.anim_rigging_tools.get_unreal_connection", return_value=conn):
        result = call()
    with pytest.raises(EnvelopeAssertionError, match="queued"):
        assert_executed(result, command)


def test_create_ik_rig_factory_mode_executed():
    payload = {
        "success": True,
        "data": {
            "command": "create_ik_rig",
            "executed": True,
            "asset_path": "/Game/IK/IKRig_Robot",
            "asset_name": "IKRig_Robot",
            "mode": "factory",
        },
    }
    conn = _conn(payload)
    with patch("server.anim_rigging_tools.get_unreal_connection", return_value=conn):
        result = art.create_ik_rig(asset_path="/Game/IK", asset_name="IKRig_Robot", skeletal_mesh_path="/Game/SK/SK_Robot")
    data = assert_executed(result, "create_ik_rig")
    assert data.get("mode") == "factory"


def test_create_ik_rig_metadata_fallback_executed():
    payload = {
        "success": True,
        "data": {
            "command": "create_ik_rig",
            "executed": True,
            "host_asset_path": "/Game/SK/SK_Robot",
            "host_asset_class": "/Script/Engine.SkeletalMesh",
            "wanted_class": "/Script/IKRig.IKRigDefinition",
            "wanted_asset_name": "IKRig_Robot",
            "wanted_package_path": "/Game/IK",
            "factory_unavailable_reason": "factory class '/Script/IKRigEditor.IKRigDefinitionFactory' is not a UFactory or is missing.",
            "mcp_metadata_keys_persisted": 3,
            "mode": "metadata_fallback",
        },
    }
    conn = _conn(payload)
    with patch("server.anim_rigging_tools.get_unreal_connection", return_value=conn):
        result = art.create_ik_rig(skeletal_mesh_path="/Game/SK/SK_Robot")
    data = assert_executed(result, "create_ik_rig")
    assert data.get("mode") == "metadata_fallback"
    assert data.get("host_asset_path") == "/Game/SK/SK_Robot"


def test_create_ik_retargeter_metadata_fallback_executed():
    payload = {
        "success": True,
        "data": {
            "command": "create_ik_retargeter",
            "executed": True,
            "host_asset_path": "/Game/IK/IKRig_Hero",
            "host_asset_class": "/Script/IKRig.IKRigDefinition",
            "wanted_class": "/Script/IKRig.IKRetargeter",
            "wanted_asset_name": "IKRetarget_Hero_to_Robot",
            "wanted_package_path": "/Game/IK",
            "factory_unavailable_reason": "factory class '/Script/IKRigEditor.IKRetargeterFactory' is not a UFactory or is missing.",
            "mcp_metadata_keys_persisted": 5,
            "source_ik_rig_path": "/Game/IK/IKRig_Hero",
            "target_ik_rig_path": "/Game/IK/IKRig_Robot",
            "mode": "metadata_fallback",
        },
    }
    conn = _conn(payload)
    with patch("server.anim_rigging_tools.get_unreal_connection", return_value=conn):
        result = art.create_ik_retargeter(
            asset_path="/Game/IK",
            asset_name="IKRetarget_Hero_to_Robot",
            source_ik_rig="/Game/IK/IKRig_Hero",
            target_ik_rig="/Game/IK/IKRig_Robot",
        )
    data = assert_executed(result, "create_ik_retargeter")
    assert data.get("mode") == "metadata_fallback"
    assert data.get("source_ik_rig_path") == "/Game/IK/IKRig_Hero"


def test_add_anim_state_legacy_kwarg_state_machine_forwarded_as_graph_name():
    conn = _conn(_executed("add_anim_state"))
    with patch("server.anim_rigging_tools.get_unreal_connection", return_value=conn):
        art.add_anim_state("/Game/AB_Hero", "Locomotion", "Run")
    args, _ = conn.send_command.call_args
    assert args[0] == "add_anim_state"
    payload = args[1]
    # Both legacy and new field present.
    assert payload["state_machine"] == "Locomotion"
    assert payload.get("graph_name") == "Locomotion"
    assert payload["state_name"] == "Run"


def test_add_notify_state_forwards_anim_path_and_notify_class():
    conn = _conn(_executed("add_notify_state"))
    with patch("server.anim_rigging_tools.get_unreal_connection", return_value=conn):
        art.add_notify_state("/Game/Anim/A_Idle", "AnimNotifyState_Trail", 0.0, 1.0)
    args, _ = conn.send_command.call_args
    payload = args[1]
    assert payload["anim_path"] == "/Game/Anim/A_Idle"
    assert payload["anim_sequence_path"] == "/Game/Anim/A_Idle"
    assert payload["notify_class"] == "AnimNotifyState_Trail"
    assert payload["notify_state_class"] == "AnimNotifyState_Trail"
