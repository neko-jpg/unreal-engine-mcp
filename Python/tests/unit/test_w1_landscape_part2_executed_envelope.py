"""234-stubs W1 (#80): executed-envelope tests for Landscape Part 2.

Pairs with the C++ promotion of 8 more handlers in
`Plugins/UnrealMCP/Source/UnrealMCP/Private/Commands/EpicUnrealMCPLandscapeCommands.cpp`
from `queued: true` to the canonical executed envelope. All handlers go
through the `LandscapeMetaPersist` helper; `set_landscape_section_component`
additionally writes `ALandscape::NumSubsections` / `SubsectionSizeQuads`
directly, and `add_road_spline` resolves the optional road mesh via
`StaticLoadObject`.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import server.landscape_tools as lt
from utils.envelope import EnvelopeAssertionError, assert_executed


def _conn(payload):
    m = MagicMock()
    m.send_command.return_value = payload
    return m


def _executed(command, **extra):
    data = {
        "command": command,
        "executed": True,
        "actor_name": extra.pop("actor_name", "Landscape_0"),
        "actor_label": extra.pop("actor_label", "Landscape"),
        "resolved_by": extra.pop("resolved_by", "actor_name"),
        "mcp_metadata_keys_persisted": extra.pop("mcp_metadata_keys_persisted", 3),
    }
    data.update(extra)
    return {"success": True, "data": data}


PART2_COMMANDS = [
    ("set_landscape_section_component",
     lambda: lt.set_landscape_section_component("Landscape_0", sections_per_component=2, quads_per_section=63)),
    ("import_landscape_heightmap",
     lambda: lt.import_landscape_heightmap("Landscape_0", "C:/maps/heightmap.png", format="png", scale=1.0)),
    ("export_landscape_heightmap",
     lambda: lt.export_landscape_heightmap("Landscape_0", "C:/out/heightmap.png", format="png")),
    ("create_landscape_paint_layer",
     lambda: lt.create_landscape_paint_layer("Landscape_0", "Soil", layer_info_path="/Game/Land/LI_Soil")),
    ("set_landscape_layer_blend",
     lambda: lt.set_landscape_layer_blend("Landscape_0", "Soil", weight=0.65)),
    ("add_landscape_spline",
     lambda: lt.add_landscape_spline("Landscape_0", [[0, 0], [100, 0], [200, 50]], segment_length=128.0)),
    ("add_road_spline",
     lambda: lt.add_road_spline("Landscape_0", [[0, 0], [500, 0]], road_mesh_path="/Game/Road/SM_Road", road_width=400.0)),
    ("carve_river_terrain",
     lambda: lt.carve_river_terrain("Landscape_0", water_body_actor="WB_River_0", carve_depth=300.0, bank_slope=0.4)),
]


@pytest.mark.parametrize("command,call", PART2_COMMANDS)
def test_part2_promoted_handler_returns_executed_envelope(command, call):
    conn = _conn(_executed(command))
    with patch("server.landscape_tools.get_unreal_connection", return_value=conn):
        result = call()
    data = assert_executed(result, command)
    assert data.get("command") == command


@pytest.mark.parametrize("command,call", PART2_COMMANDS)
def test_part2_promoted_handler_rejects_queued_regression(command, call):
    conn = _conn({"success": True, "data": {"command": command, "queued": True, "hint": "fallback"}})
    with patch("server.landscape_tools.get_unreal_connection", return_value=conn):
        result = call()
    with pytest.raises(EnvelopeAssertionError, match="queued"):
        assert_executed(result, command)


def test_set_layer_blend_surfaces_clamp_flag():
    payload = _executed("set_landscape_layer_blend", layer_name="Soil", weight=1.0, weight_clamped=True)
    conn = _conn(payload)
    with patch("server.landscape_tools.get_unreal_connection", return_value=conn):
        result = lt.set_landscape_layer_blend("Landscape_0", "Soil", weight=2.5)
    data = assert_executed(result, "set_landscape_layer_blend")
    assert data.get("weight_clamped") is True


def test_add_road_spline_surfaces_mesh_resolution():
    payload = _executed("add_road_spline", point_count=2, road_width=400.0, road_mesh_path="/Game/Road/SM_Road", mesh_resolved=True)
    conn = _conn(payload)
    with patch("server.landscape_tools.get_unreal_connection", return_value=conn):
        result = lt.add_road_spline("Landscape_0", [[0, 0], [500, 0]], road_mesh_path="/Game/Road/SM_Road")
    data = assert_executed(result, "add_road_spline")
    assert data.get("mesh_resolved") is True


def test_add_landscape_spline_validates_min_two_points():
    """Python-side guard fires before any send_command."""
    conn = _conn(_executed("add_landscape_spline"))
    with patch("server.landscape_tools.get_unreal_connection", return_value=conn):
        result = lt.add_landscape_spline("Landscape_0", [[0, 0]])
    assert result.get("success") in (False, None)
    msg = str(result.get("error") or result.get("message") or "")
    assert ">= 2" in msg or "points" in msg
    conn.send_command.assert_not_called()


def test_section_component_payload_has_both_fields():
    conn = _conn(_executed("set_landscape_section_component"))
    with patch("server.landscape_tools.get_unreal_connection", return_value=conn):
        lt.set_landscape_section_component("Landscape_0", sections_per_component=2, quads_per_section=127)
    args, _ = conn.send_command.call_args
    assert args[0] == "set_landscape_section_component"
    assert args[1]["sections_per_component"] == 2
    assert args[1]["quads_per_section"] == 127
    assert args[1]["actor_name"] == "Landscape_0"
