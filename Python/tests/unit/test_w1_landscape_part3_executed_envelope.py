"""234-stubs W1 (#80): executed-envelope tests for Landscape Part 3.

Closes #80 in tandem with the C++ promotion of the last 6 brush handlers
in `Plugins/UnrealMCP/Source/UnrealMCP/Private/Commands/EpicUnrealMCPLandscapeCommands.cpp`.
After this PR every handler in the Landscape category returns
`executed: true`; only the `LandscapeQueued` helper *definition* keeps
the `queued: true` literal in source so the wave-close PR can drop the
baseline.
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
        "mcp_metadata_keys_persisted": extra.pop("mcp_metadata_keys_persisted", 4),
    }
    data.update(extra)
    return {"success": True, "data": data}


PART3_COMMANDS = [
    ("landscape_sculpt",
     lambda: lt.landscape_sculpt("Landscape_0", brush_radius=120.0, brush_strength=0.7, location_xy=[10.0, 20.0])),
    ("landscape_smooth",
     lambda: lt.landscape_smooth("Landscape_0", brush_radius=180.0, iterations=3)),
    ("landscape_flatten",
     lambda: lt.landscape_flatten("Landscape_0", target_height=200.0, brush_radius=160.0)),
    ("landscape_ramp",
     lambda: lt.landscape_ramp("Landscape_0", [0, 0], [500, 0], ramp_height=150.0, ramp_width=240.0)),
    ("landscape_erosion",
     lambda: lt.landscape_erosion("Landscape_0", iterations=8, strength=0.6)),
    ("landscape_noise",
     lambda: lt.landscape_noise("Landscape_0", frequency=0.1, amplitude=64.0)),
]


@pytest.mark.parametrize("command,call", PART3_COMMANDS)
def test_part3_promoted_handler_returns_executed_envelope(command, call):
    conn = _conn(_executed(command))
    with patch("server.landscape_tools.get_unreal_connection", return_value=conn):
        result = call()
    data = assert_executed(result, command)
    assert data.get("command") == command


@pytest.mark.parametrize("command,call", PART3_COMMANDS)
def test_part3_promoted_handler_rejects_queued_regression(command, call):
    conn = _conn({"success": True, "data": {"command": command, "queued": True, "hint": "fallback"}})
    with patch("server.landscape_tools.get_unreal_connection", return_value=conn):
        result = call()
    with pytest.raises(EnvelopeAssertionError, match="queued"):
        assert_executed(result, command)


def test_landscape_ramp_validates_start_xy():
    conn = _conn(_executed("landscape_ramp"))
    with patch("server.landscape_tools.get_unreal_connection", return_value=conn):
        result = lt.landscape_ramp("Landscape_0", [0], [100, 0])
    assert result.get("success") in (False, None)
    conn.send_command.assert_not_called()


def test_landscape_ramp_validates_end_xy():
    conn = _conn(_executed("landscape_ramp"))
    with patch("server.landscape_tools.get_unreal_connection", return_value=conn):
        result = lt.landscape_ramp("Landscape_0", [0, 0], [])
    assert result.get("success") in (False, None)
    conn.send_command.assert_not_called()


def test_landscape_sculpt_default_location_is_zero_zero():
    """Legacy call without location_xy still echoes [0, 0] in payload."""
    conn = _conn(_executed("landscape_sculpt"))
    with patch("server.landscape_tools.get_unreal_connection", return_value=conn):
        lt.landscape_sculpt("Landscape_0")
    args, _ = conn.send_command.call_args
    assert args[1]["location_xy"] == [0.0, 0.0]
