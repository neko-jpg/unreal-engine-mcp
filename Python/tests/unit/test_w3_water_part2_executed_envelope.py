"""W3 unit tests for water_tools -- 7 promoted executed-envelope handlers (part 2)."""
import unittest
from unittest.mock import patch, MagicMock

import server.water_tools as m


def _mock_send_command(cmd_type, params):
    return {"success": True, "data": {"executed": True, "command": cmd_type, **(params or {})}}


def _conn():
    c = MagicMock()
    c.send_command = MagicMock(side_effect=_mock_send_command)
    return c


class TestWaterPart2ExecutedEnvelope(unittest.TestCase):

    @patch("server.water_tools.get_unreal_connection", return_value=_conn())
    def test_configure_water_flow(self, mock_conn):
        result = m.configure_water_flow(actor_name="TestRiver", flow_velocity=150.0)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.water_tools.get_unreal_connection", return_value=_conn())
    def test_configure_buoyancy(self, mock_conn):
        result = m.configure_buoyancy(actor_name="TestActor", weight=2.0, damping=0.8)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.water_tools.get_unreal_connection", return_value=_conn())
    def test_configure_water_mesh_actor(self, mock_conn):
        result = m.configure_water_mesh_actor(actor_name="TestWaterZone", tile_size=3000.0)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.water_tools.get_unreal_connection", return_value=_conn())
    def test_configure_underwater_post_process(self, mock_conn):
        result = m.configure_underwater_post_process(post_process_actor="TestWaterBody")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.water_tools.get_unreal_connection", return_value=_conn())
    def test_configure_shoreline(self, mock_conn):
        result = m.configure_shoreline(actor_name="TestLake", smoothness=0.7)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.water_tools.get_unreal_connection", return_value=_conn())
    def test_configure_water_landscape_carving(self, mock_conn):
        result = m.configure_water_landscape_carving(landscape_actor="TestRiver", enable=True)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.water_tools.get_unreal_connection", return_value=_conn())
    def test_attach_floating_actor(self, mock_conn):
        pontoons = [{"x": 0, "y": 0, "z": 0}, {"x": 100, "y": 0, "z": 0}]
        result = m.attach_floating_actor(actor_name="TestBoat", pontoon_locations=pontoons)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))


if __name__ == "__main__":
    unittest.main()
