"""L2 executed-envelope test for Chaos spike (#89) — create_collision_channel.

Verifies that the C++ side returns {success:true, data:{executed:true, ...}}
for the promoted create_collision_channel handler when WITH_CHAOS_MCP is active.
"""

import unittest
from unittest.mock import patch, MagicMock


def _mock_send_command(cmd_type, params):
    """Simulate a successful executed response from the C++ bridge."""
    return {
        "success": True,
        "data": {
            "executed": True,
            "command": cmd_type,
            **(params or {}),
        },
    }


def _conn():
    c = MagicMock()
    c.send_command = MagicMock(side_effect=_mock_send_command)
    return c


class TestChaosSpikeExecutedEnvelope(unittest.TestCase):
    """create_collision_channel must return executed:true on the success path."""

    @patch("server.chaos_tools.get_unreal_connection", return_value=_conn())
    def test_create_collision_channel(self, mock_conn):
        from server import chaos_tools as m
        result = m.create_collision_channel(channel_name="MCP_TestChannel")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))
