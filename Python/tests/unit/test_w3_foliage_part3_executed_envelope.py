"""234-stubs W3 (#90): executed-envelope tests for Foliage handlers (part 3/3, final 4 handlers).

This file pairs with the C++ promotion of 4 handlers in
`EpicUnrealMCPFoliageCommands.cpp` from `queued: true` to the canonical
`{success:true, data:{executed:true, ...}}` envelope.

Handlers promoted in this part:
- spawn_biome_foliage — composite procedural spawner + volume
- create_grass_type — ULandscapeGrassType asset creation
- bind_landscape_grass — Bind ULandscapeGrassType to ULandscapeComponent
- configure_pivot_painter — PivotPainter wind configuration
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


FOLIAGE_PART3_COMMANDS = [
    ("spawn_biome_foliage", lambda: fol.spawn_biome_foliage("temperate", [0.0, 0.0, 0.0])),
    ("create_grass_type", lambda: fol.create_grass_type("/Game/Foliage", "Grass_New")),
    ("bind_landscape_grass", lambda: fol.bind_landscape_grass("Landscape", "/Game/Foliage/Grass_New")),
    ("configure_pivot_painter", lambda: fol.configure_pivot_painter("/Game/Foliage/FT_Oak", 1.0)),
]


@pytest.mark.parametrize("command,call", FOLIAGE_PART3_COMMANDS)
def test_foliage_part3_promoted_handler_returns_executed_envelope(command, call):
    payload = _executed_envelope(command)
    conn = _conn_returning(payload)
    with patch("server.foliage_tools.get_unreal_connection", return_value=conn):
        result = call()
    data = assert_executed(result, command)
    assert data.get("command") == command


@pytest.mark.parametrize("command,call", FOLIAGE_PART3_COMMANDS)
def test_foliage_part3_promoted_handler_rejects_queued_regression(command, call):
    queued = {"success": True, "data": {"command": command, "queued": True, "hint": "fallback"}}
    conn = _conn_returning(queued)
    with patch("server.foliage_tools.get_unreal_connection", return_value=conn):
        result = call()
    with pytest.raises(EnvelopeAssertionError, match="queued"):
        assert_executed(result, command)
