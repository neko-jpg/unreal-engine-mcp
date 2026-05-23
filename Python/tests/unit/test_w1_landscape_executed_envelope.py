"""234-stubs W1 (#80): executed-envelope tests for Landscape Part 1.

Pairs with the C++ promotion of 8 handlers in
`Plugins/UnrealMCP/Source/UnrealMCP/Private/Commands/EpicUnrealMCPLandscapeCommands.cpp`
from `queued: true` to the canonical
`{success:true, data:{executed:true, ...}}` envelope.

Each Python tool now accepts the extended kwargs that the C++ payload
expects (e.g. `mcp_id`, `collision_mip_level`, `shape`, etc.), and each
handler is asserted with `utils.envelope.assert_executed` plus a paired
queued-regression guard.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import server.landscape_tools as lt
from utils.envelope import EnvelopeAssertionError, assert_executed


def _conn_returning(payload):
    m = MagicMock()
    m.send_command.return_value = payload
    return m


def _executed_envelope(command, **extra):
    data = {
        "command": command,
        "executed": True,
        "actor_name": extra.pop("actor_name", "Landscape_0"),
        "actor_label": extra.pop("actor_label", "Landscape"),
        "resolved_by": extra.pop("resolved_by", "mcp_id"),
        "mcp_metadata_keys_persisted": extra.pop("mcp_metadata_keys_persisted", 3),
    }
    data.update(extra)
    return {"success": True, "data": data}


PART1_COMMANDS = [
    ("set_landscape_size",
     lambda: lt.set_landscape_size(actor_name="Landscape_0", sections_per_component=2, quads_per_section=63, component_size_quads=63)),
    ("set_landscape_collision",
     lambda: lt.set_landscape_collision(actor_name="Landscape_0", enable=True, collision_mip_level=1, simple_collision_mip_level=2, generate_overlap_events=True)),
    ("set_landscape_grass_output",
     lambda: lt.set_landscape_grass_output(grass_type_path="/Game/Grass/G_Default", actor_name="Landscape_0", layer_name="Soil", density=0.7)),
    ("add_landscape_hole",
     lambda: lt.add_landscape_hole(actor_name="Landscape_0", shape="rect", x=0.0, y=0.0, width=512.0, height=512.0)),
    ("apply_landscape_material",
     lambda: lt.apply_landscape_material(actor_name="Landscape_0", material_path="/Game/Mat/M_Land")),
    ("attach_landscape_rvt",
     lambda: lt.attach_landscape_rvt(rvt_path="/Game/RVT/RVT_Color", actor_name="Landscape_0")),
    ("set_landscape_nanite",
     lambda: lt.set_landscape_nanite(enable=True, actor_name="Landscape_0")),
    ("set_landscape_world_partition",
     lambda: lt.set_landscape_world_partition(grid_size=4, actor_name="Landscape_0", include_grid_size_in_name=True)),
]


@pytest.mark.parametrize("command,call", PART1_COMMANDS)
def test_part1_promoted_handler_returns_executed_envelope(command, call):
    payload = _executed_envelope(command)
    conn = _conn_returning(payload)
    with patch("server.landscape_tools.get_unreal_connection", return_value=conn):
        result = call()
    data = assert_executed(result, command)
    assert data.get("command") == command


@pytest.mark.parametrize("command,call", PART1_COMMANDS)
def test_part1_promoted_handler_rejects_queued_regression(command, call):
    queued = {"success": True, "data": {"command": command, "queued": True, "hint": "fallback"}}
    conn = _conn_returning(queued)
    with patch("server.landscape_tools.get_unreal_connection", return_value=conn):
        result = call()
    with pytest.raises(EnvelopeAssertionError, match="queued"):
        assert_executed(result, command)


def test_apply_landscape_material_sends_material_path():
    conn = _conn_returning(_executed_envelope("apply_landscape_material"))
    with patch("server.landscape_tools.get_unreal_connection", return_value=conn):
        lt.apply_landscape_material(actor_name="Landscape_0", material_path="/Game/M/M_Land", mcp_id="mcp.land.0")
    args, _ = conn.send_command.call_args
    assert args[0] == "apply_landscape_material"
    assert args[1]["material_path"] == "/Game/M/M_Land"
    assert args[1]["actor_name"] == "Landscape_0"
    assert args[1]["mcp_id"] == "mcp.land.0"


def test_set_landscape_size_uses_legacy_args():
    """Legacy callers passing width_quads/height_quads must still work."""
    conn = _conn_returning(_executed_envelope("set_landscape_size"))
    with patch("server.landscape_tools.get_unreal_connection", return_value=conn):
        lt.set_landscape_size("Landscape_0", 1024, 1024)
    args, _ = conn.send_command.call_args
    assert args[0] == "set_landscape_size"
    assert args[1]["actor_name"] == "Landscape_0"
    assert args[1].get("width_quads") == 1024
    assert args[1].get("height_quads") == 1024


def test_resolve_failure_surfaces_available_labels():
    err = {
        "success": False,
        "error": "'apply_landscape_material': no ALandscape found. Pass mcp_id, actor_name, or actor_label.",
        "available_landscape_labels": ["Hero_Island", "Test_Plate"],
    }
    conn = _conn_returning(err)
    with patch("server.landscape_tools.get_unreal_connection", return_value=conn):
        result = lt.apply_landscape_material(actor_name="DoesNotExist", material_path="/Game/M/X")
    assert result.get("success") in (False, None)
    msg = str(result.get("error") or result.get("message") or "")
    assert "no ALandscape found" in msg or "available_landscape_labels" in result
