"""234-stubs W3 (#90): executed-envelope tests for Foliage handlers (part 4/4, 8 handlers).

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


FOLIAGE_PART4_COMMANDS = [
    ("foliage_paint", lambda: fol.foliage_paint("/Game/Foliage/FT_Oak", [0, 0, 0], 500.0)),
    ("foliage_erase", lambda: fol.foliage_erase("/Game/Foliage/FT_Oak", [0, 0, 0], 500.0)),
    ("set_foliage_lod", lambda: fol.set_foliage_lod("/Game/Foliage/FT_Oak", [0.5])),
    ("create_procedural_foliage_spawner", lambda: fol.create_procedural_foliage_spawner("/Game/Foliage", "PFS_New")),
    ("create_procedural_foliage_volume", lambda: fol.create_procedural_foliage_volume("PFV_Default")),
    ("set_procedural_foliage_seed", lambda: fol.set_procedural_foliage_seed("PFV_Default", 42)),
    ("set_foliage_nanite", lambda: fol.set_foliage_nanite("/Game/Foliage/FT_Oak", True)),
    ("set_foliage_wind", lambda: fol.set_foliage_wind("/Game/Foliage/FT_Oak", "")),
]


@pytest.mark.parametrize("command,call", FOLIAGE_PART4_COMMANDS)
def test_foliage_part4_promoted_handler_returns_executed_envelope(command, call):
    payload = _executed_envelope(command)
    conn = _conn_returning(payload)
    with patch("server.foliage_tools.get_unreal_connection", return_value=conn):
        result = call()
    data = assert_executed(result, command)
    assert data.get("command") == command


@pytest.mark.parametrize("command,call", FOLIAGE_PART4_COMMANDS)
def test_foliage_part4_promoted_handler_rejects_queued_regression(command, call):
    queued = {"success": True, "data": {"command": command, "queued": True, "hint": "fallback"}}
    conn = _conn_returning(queued)
    with patch("server.foliage_tools.get_unreal_connection", return_value=conn):
        result = call()
    with pytest.raises(EnvelopeAssertionError, match="queued"):
        assert_executed(result, command)
