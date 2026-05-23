"""L2 executed-envelope tests for PCG #91 part1 (8 promoted handlers).

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


class TestPCGPart1ExecutedEnvelope(unittest.TestCase):
    """Each PCG handler must return executed:true on the success path."""

    @patch("server.pcg_tools.get_unreal_connection", return_value=_conn())
    def test_add_pcg_component(self, mock_conn):
        from server import pcg_tools as m
        result = m.add_pcg_component(actor_name="TestActor", graph_path="/Game/PCG/MyGraph")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.pcg_tools.get_unreal_connection", return_value=_conn())
    def test_create_pcg_volume(self, mock_conn):
        from server import pcg_tools as m
        result = m.create_pcg_volume(actor_name="PCGVolume", extent_xyz=[2000.0, 2000.0, 500.0])
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.pcg_tools.get_unreal_connection", return_value=_conn())
    def test_add_pcg_node(self, mock_conn):
        from server import pcg_tools as m
        result = m.add_pcg_node(graph_path="/Game/PCG/MyGraph", node_type="SurfaceSampler")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.pcg_tools.get_unreal_connection", return_value=_conn())
    def test_connect_pcg_nodes(self, mock_conn):
        from server import pcg_tools as m
        result = m.connect_pcg_nodes(graph_path="/Game/PCG/MyGraph", from_node="Source", to_node="Target")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.pcg_tools.get_unreal_connection", return_value=_conn())
    def test_set_pcg_graph_parameter(self, mock_conn):
        from server import pcg_tools as m
        result = m.set_pcg_graph_parameter(graph_path="/Game/PCG/MyGraph", parameter="Seed", value="42")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.pcg_tools.get_unreal_connection", return_value=_conn())
    def test_configure_pcg_spline_sampler(self, mock_conn):
        from server import pcg_tools as m
        result = m.configure_pcg_spline_sampler(graph_path="/Game/PCG/MyGraph", spline_actor="SplineActor")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.pcg_tools.get_unreal_connection", return_value=_conn())
    def test_configure_pcg_surface_sampler(self, mock_conn):
        from server import pcg_tools as m
        result = m.configure_pcg_surface_sampler(graph_path="/Game/PCG/MyGraph", surface_actor="Landscape", density=2.0)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.pcg_tools.get_unreal_connection", return_value=_conn())
    def test_configure_pcg_static_mesh_spawner(self, mock_conn):
        from server import pcg_tools as m
        result = m.configure_pcg_static_mesh_spawner(graph_path="/Game/PCG/MyGraph", mesh_path="/Game/Meshes/SM_Rock")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))


if __name__ == "__main__":
    unittest.main()
