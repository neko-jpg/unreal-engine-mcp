"""L2 executed-envelope tests for PCG #91 spike (1 promoted handler).

Verifies that the C++ side returns {success:true, data:{executed:true, ...}}
for the promoted create_pcg_graph handler. These tests use a mocked Unreal
connection that returns a canned executed envelope.
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


class TestPCGSpikeExecutedEnvelope(unittest.TestCase):
    """The promoted PCG handler must return executed:true on the success path."""

    @patch("server.pcg_tools.get_unreal_connection", return_value=_conn())
    def test_create_pcg_graph(self, mock_conn):
        from server import pcg_tools as m
        result = m.create_pcg_graph(asset_path="/Game/PCG", asset_name="PCGGraph_New")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))


if __name__ == "__main__":
    unittest.main()
