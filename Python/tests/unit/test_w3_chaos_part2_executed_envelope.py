"""L2 executed-envelope tests for Chaos #89 part 2 (10 promoted handlers).

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


class TestChaosPart2ExecutedEnvelope(unittest.TestCase):
    """Each Chaos handler must return executed:true on the success path."""

    @patch("server.chaos_tools.get_unreal_connection", return_value=_conn())
    def test_set_vehicle_wheel(self, mock_conn):
        from server import chaos_tools as m
        result = m.set_vehicle_wheel(actor_name="ChaosVehicle", wheel_index=0, wheel_class="ChaosWheel")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.chaos_tools.get_unreal_connection", return_value=_conn())
    def test_set_vehicle_suspension(self, mock_conn):
        from server import chaos_tools as m
        result = m.set_vehicle_suspension(actor_name="ChaosVehicle", wheel_index=0, stiffness=100.0)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.chaos_tools.get_unreal_connection", return_value=_conn())
    def test_set_vehicle_engine_torque(self, mock_conn):
        from server import chaos_tools as m
        result = m.set_vehicle_engine_torque(actor_name="ChaosVehicle", torque_curve=[])
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.chaos_tools.get_unreal_connection", return_value=_conn())
    def test_set_cloth_settings(self, mock_conn):
        from server import chaos_tools as m
        result = m.set_cloth_settings(skeletal_mesh_path="/Game/Meshes/SK_Cloth", damping=0.5)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.chaos_tools.get_unreal_connection", return_value=_conn())
    def test_create_chaos_cloth_asset(self, mock_conn):
        from server import chaos_tools as m
        result = m.create_chaos_cloth_asset(asset_path="/Game/Chaos", asset_name="ChaosCloth_New")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.chaos_tools.get_unreal_connection", return_value=_conn())
    def test_set_groom_physics(self, mock_conn):
        from server import chaos_tools as m
        result = m.set_groom_physics(groom_path="/Game/Groom/Hair", enable=True)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.chaos_tools.get_unreal_connection", return_value=_conn())
    def test_set_ragdoll(self, mock_conn):
        from server import chaos_tools as m
        result = m.set_ragdoll(skeletal_actor="SK_Hero", enable=True)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.chaos_tools.get_unreal_connection", return_value=_conn())
    def test_edit_physics_asset_body(self, mock_conn):
        from server import chaos_tools as m
        result = m.edit_physics_asset_body(physics_asset_path="/Game/Physics/PA_Hero", bone="spine_01", mass=2.0)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.chaos_tools.get_unreal_connection", return_value=_conn())
    def test_edit_physics_asset_constraint(self, mock_conn):
        from server import chaos_tools as m
        result = m.edit_physics_asset_constraint(physics_asset_path="/Game/Physics/PA_Hero", constraint_name="spine_01_spine_02")
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))

    @patch("server.chaos_tools.get_unreal_connection", return_value=_conn())
    def test_attach_chaos_visual_debugger(self, mock_conn):
        from server import chaos_tools as m
        result = m.attach_chaos_visual_debugger(enable=True)
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("data", {}).get("executed"))


if __name__ == "__main__":
    unittest.main()
