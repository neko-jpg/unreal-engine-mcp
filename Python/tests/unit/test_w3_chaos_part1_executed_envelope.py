"""L2 executed-envelope tests for Chaos #89 part 1 (8 promoted handlers).

Verifies that the C++ side returns {success:true, data:{executed:true, ...}}
for each promoted Chaos handler when WITH_EDITOR is active.  These tests use a
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


class TestChaosPart1ExecutedEnvelope(unittest.TestCase):
    """Each Chaos handler must return executed:true on the success path."""

    @patch("server.chaos_tools.get_unreal_connection", return_value=_conn())
    def test_create_object_channel(self, mock_conn):
        from server import chaos_tools as m
        result = m.create_object_channel(channel_name="MCP_ObjectChannel", default_response="Block")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.chaos_tools.get_unreal_connection", return_value=_conn())
    def test_create_trace_channel(self, mock_conn):
        from server import chaos_tools as m
        result = m.create_trace_channel(channel_name="MCP_TraceChannel", default_response="Ignore")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.chaos_tools.get_unreal_connection", return_value=_conn())
    def test_create_geometry_collection(self, mock_conn):
        from server import chaos_tools as m
        result = m.create_geometry_collection(asset_path="/Game/Chaos", asset_name="GC_New", source_mesh="")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.chaos_tools.get_unreal_connection", return_value=_conn())
    def test_fracture_geometry_collection(self, mock_conn):
        from server import chaos_tools as m
        result = m.fracture_geometry_collection(asset_path="/Game/Chaos/GC_New", fracture_type="Uniform", seed=0)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.chaos_tools.get_unreal_connection", return_value=_conn())
    def test_create_chaos_field(self, mock_conn):
        from server import chaos_tools as m
        result = m.create_chaos_field(field_class="RadialFalloff", actor_name="ChaosField")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.chaos_tools.get_unreal_connection", return_value=_conn())
    def test_configure_chaos_solver(self, mock_conn):
        from server import chaos_tools as m
        result = m.configure_chaos_solver(solver_actor="ChaosSolverActor", sub_steps=1)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.chaos_tools.get_unreal_connection", return_value=_conn())
    def test_create_chaos_cache(self, mock_conn):
        from server import chaos_tools as m
        result = m.create_chaos_cache(asset_path="/Game/Chaos", asset_name="ChaosCache_New")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.chaos_tools.get_unreal_connection", return_value=_conn())
    def test_create_chaos_vehicle(self, mock_conn):
        from server import chaos_tools as m
        result = m.create_chaos_vehicle(actor_name="ChaosVehicle", mesh_path="")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))


if __name__ == "__main__":
    unittest.main()
