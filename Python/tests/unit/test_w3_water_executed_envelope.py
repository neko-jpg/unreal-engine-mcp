"""W3 unit tests for water_tools -- 8 promoted executed-envelope handlers."""
import unittest
from unittest.mock import patch, MagicMock

import server.water_tools as m


def _mock_send_command(cmd_type, params):
    return {"success": True, "data": {"executed": True, "command": cmd_type, **(params or {})}}


def _conn():
    c = MagicMock()
    c.send_command = MagicMock(side_effect=_mock_send_command)
    return c


class TestWaterPart1ExecutedEnvelope(unittest.TestCase):

    @patch("server.water_tools.get_unreal_connection", return_value=_conn())
    def test_enable_water_plugin(self, mock_conn):
        result = m.enable_water_plugin()
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.water_tools.get_unreal_connection", return_value=_conn())
    def test_spawn_water_body_ocean(self, mock_conn):
        result = m.spawn_water_body_ocean(actor_name="TestOcean")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.water_tools.get_unreal_connection", return_value=_conn())
    def test_spawn_water_body_lake(self, mock_conn):
        pts = [{"x": 0, "y": 0, "z": 0}, {"x": 100, "y": 0, "z": 0}]
        result = m.spawn_water_body_lake(actor_name="TestLake", spline_points=pts)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.water_tools.get_unreal_connection", return_value=_conn())
    def test_spawn_water_body_river(self, mock_conn):
        pts = [{"x": 0, "y": 0, "z": 0}, {"x": 200, "y": 100, "z": 0}]
        result = m.spawn_water_body_river(actor_name="TestRiver", spline_points=pts)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.water_tools.get_unreal_connection", return_value=_conn())
    def test_spawn_water_body_custom(self, mock_conn):
        result = m.spawn_water_body_custom(actor_name="TestCustom")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.water_tools.get_unreal_connection", return_value=_conn())
    def test_configure_river_spline(self, mock_conn):
        pts = [{"x": 0, "y": 0, "z": 0}, {"x": 50, "y": 50, "z": 0}]
        result = m.configure_river_spline(actor_name="TestRiver", spline_points=pts)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.water_tools.get_unreal_connection", return_value=_conn())
    def test_set_water_material(self, mock_conn):
        result = m.set_water_material(actor_name="TestLake", material_path="/Game/Materials/WaterMat")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.water_tools.get_unreal_connection", return_value=_conn())
    def test_configure_water_wave(self, mock_conn):
        result = m.configure_water_wave(actor_name="TestOcean", asset_path="/Game/Waves/WaveAsset")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))


if __name__ == "__main__":
    unittest.main()
