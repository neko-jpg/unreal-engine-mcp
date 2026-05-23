"""234-stubs W3 (#90): executed-envelope tests for Foliage handlers (part 1/3, 8 handlers).

This file pairs with the C++ promotion of 8 handlers in
`EpicUnrealMCPFoliageCommands.cpp` from `queued: true` to the canonical
`{success:true, data:{executed:true, ...}}` envelope.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import server.foliage_tools as fol
from utils.envelope import EnvelopeAssertionError, assert_executed


def _conn_returning(payload):
    m = MagicMock()
    m.send_command.return_value = payload
    return m


def _executed_envelope(command, **extra):
    data = {"command": command, "executed": True}
    data.update(extra)
    return {"success": True, "data": data}


FOLIAGE_COMMANDS = [
    ("create_foliage_type", lambda: fol.create_foliage_type("/Game/Foliage", "FT_Oak")),
    ("register_static_mesh_foliage", lambda: fol.register_static_mesh_foliage("/Game/Foliage/FT_Oak", "/Game/Meshes/SM_Oak")),
    ("register_actor_foliage", lambda: fol.register_actor_foliage("/Game/Foliage/FT_Oak", "/Script/Engine.StaticMeshActor")),
    ("set_foliage_density", lambda: fol.set_foliage_density("/Game/Foliage/FT_Oak", 2.5)),
    ("set_foliage_scale_range", lambda: fol.set_foliage_scale_range("/Game/Foliage/FT_Oak", 0.8, 1.2)),
    ("set_foliage_random_yaw", lambda: fol.set_foliage_random_yaw("/Game/Foliage/FT_Oak", True)),
    ("set_foliage_align_to_normal", lambda: fol.set_foliage_align_to_normal("/Game/Foliage/FT_Oak", True)),
    ("set_foliage_cull_distance", lambda: fol.set_foliage_cull_distance("/Game/Foliage/FT_Oak", 5000.0, 10000.0)),
]


@pytest.mark.parametrize("command,call", FOLIAGE_COMMANDS)
def test_foliage_promoted_handler_returns_executed_envelope(command, call):
    payload = _executed_envelope(command)
    conn = _conn_returning(payload)
    with patch("server.foliage_tools.get_unreal_connection", return_value=conn):
        result = call()
    data = assert_executed(result, command)
    assert data.get("command") == command


@pytest.mark.parametrize("command,call", FOLIAGE_COMMANDS)
def test_foliage_promoted_handler_rejects_queued_regression(command, call):
    queued = {"success": True, "data": {"command": command, "queued": True, "hint": "fallback"}}
    conn = _conn_returning(queued)
    with patch("server.foliage_tools.get_unreal_connection", return_value=conn):
        result = call()
    with pytest.raises(EnvelopeAssertionError, match="queued"):
        assert_executed(result, command)
