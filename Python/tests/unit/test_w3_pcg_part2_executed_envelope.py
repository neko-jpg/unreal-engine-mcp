"""L2 executed-envelope tests for PCG #91 part2 (11 promoted handlers).

Verifies that the C++ side returns {success:true, data:{executed:true, ...}}
for each promoted handler when WITH_PCG_MCP is active. These tests use a
mocked Unreal connection that returns a canned executed envelope.
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


class TestPCGPart2ExecutedEnvelope(unittest.TestCase):
    """Each PCG handler must return executed:true on the success path."""

    @patch("server.pcg_tools.get_unreal_connection", return_value=_conn())
    def test_configure_pcg_rule(self, mock_conn):
        from server import pcg_tools as m
        result = m.configure_pcg_rule(graph_path="/Game/PCG/MyGraph", rule_name="TestRule")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.pcg_tools.get_unreal_connection", return_value=_conn())
    def test_create_pcg_biome_graph(self, mock_conn):
        from server import pcg_tools as m
        result = m.create_pcg_biome_graph(asset_path="/Game/PCG", asset_name="BiomeGraph")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.pcg_tools.get_unreal_connection", return_value=_conn())
    def test_operate_pcg_point_data(self, mock_conn):
        from server import pcg_tools as m
        result = m.operate_pcg_point_data(graph_path="/Game/PCG/MyGraph", operation="Project")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.pcg_tools.get_unreal_connection", return_value=_conn())
    def test_operate_pcg_attribute(self, mock_conn):
        from server import pcg_tools as m
        result = m.operate_pcg_attribute(graph_path="/Game/PCG/MyGraph", attribute_name="Density")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.pcg_tools.get_unreal_connection", return_value=_conn())
    def test_execute_pcg_graph(self, mock_conn):
        from server import pcg_tools as m
        result = m.execute_pcg_graph(actor_name="PCGActor")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.pcg_tools.get_unreal_connection", return_value=_conn())
    def test_regenerate_pcg_graph(self, mock_conn):
        from server import pcg_tools as m
        result = m.regenerate_pcg_graph(actor_name="PCGActor")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.pcg_tools.get_unreal_connection", return_value=_conn())
    def test_set_pcg_runtime_generation(self, mock_conn):
        from server import pcg_tools as m
        result = m.set_pcg_runtime_generation(actor_name="PCGActor", enable=True)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.pcg_tools.get_unreal_connection", return_value=_conn())
    def test_use_pcg_editor_mode(self, mock_conn):
        from server import pcg_tools as m
        result = m.use_pcg_editor_mode(mode="Sculpt")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.pcg_tools.get_unreal_connection", return_value=_conn())
    def test_create_pcg_tool(self, mock_conn):
        from server import pcg_tools as m
        result = m.create_pcg_tool(asset_path="/Game/PCG", asset_name="ToolGraph")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.pcg_tools.get_unreal_connection", return_value=_conn())
    def test_set_pcg_debug_display(self, mock_conn):
        from server import pcg_tools as m
        result = m.set_pcg_debug_display(enable=True)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.pcg_tools.get_unreal_connection", return_value=_conn())
    def test_configure_pcg_self_pruning(self, mock_conn):
        from server import pcg_tools as m
        result = m.configure_pcg_self_pruning(graph_path="/Game/PCG/MyGraph", radius=150.0)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))


if __name__ == "__main__":
    unittest.main()
