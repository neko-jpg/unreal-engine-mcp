"""L1 unit tests for physics_tools W1-B residue."""

from unittest.mock import patch, MagicMock

import server.physics_tools as physics_tools


def _mock_conn():
    m = MagicMock()
    m.send_command.return_value = {"success": True}
    return m


class TestSetActorCollisionResponse:
    def test_sends_required(self):
        with patch("server.physics_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            physics_tools.set_actor_collision_response("A", "Pawn", "Overlap")
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload == {"actor_name": "A", "channel": "Pawn", "response": "Overlap"}

    def test_rejects_unknown_response(self):
        with patch("server.physics_tools.get_unreal_connection", return_value=_mock_conn()):
            r = physics_tools.set_actor_collision_response("A", "Pawn", "Hover")
        assert r.get("success") is False

    def test_rejects_empty_actor(self):
        with patch("server.physics_tools.get_unreal_connection", return_value=_mock_conn()):
            r = physics_tools.set_actor_collision_response("", "Pawn", "Block")
        assert r.get("success") is False


class TestSetConstraintLimits:
    def test_sends_motion(self):
        with patch("server.physics_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            physics_tools.set_constraint_limits(
                "C1",
                linear_x_motion="Locked",
                angular_swing1_motion="Limited",
                angular_swing1_limit_degrees=45.0,
            )
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["linear_x_motion"] == "Locked"
        assert payload["angular_swing1_motion"] == "Limited"
        assert payload["angular_swing1_limit_degrees"] == 45.0

    def test_rejects_unknown_motion(self):
        with patch("server.physics_tools.get_unreal_connection", return_value=_mock_conn()):
            r = physics_tools.set_constraint_limits("C1", linear_x_motion="Bouncy")
        assert r.get("success") is False

    def test_rejects_negative_limit(self):
        with patch("server.physics_tools.get_unreal_connection", return_value=_mock_conn()):
            r = physics_tools.set_constraint_limits(
                "C1",
                angular_twist_motion="Limited",
                angular_twist_limit_degrees=-1.0,
            )
        assert r.get("success") is False

    def test_rejects_no_fields(self):
        with patch("server.physics_tools.get_unreal_connection", return_value=_mock_conn()):
            r = physics_tools.set_constraint_limits("C1")
        assert r.get("success") is False


class TestSetConstraintMotor:
    def test_sends_drive(self):
        with patch("server.physics_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            physics_tools.set_constraint_motor(
                "C1",
                linear_velocity_drive=True,
                linear_velocity_target=[10.0, 0.0, 0.0],
            )
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["linear_velocity_drive"] is True
        assert payload["linear_velocity_target"] == [10.0, 0.0, 0.0]

    def test_rejects_bad_target(self):
        with patch("server.physics_tools.get_unreal_connection", return_value=_mock_conn()):
            r = physics_tools.set_constraint_motor("C1", linear_velocity_target=[1.0])
        assert r.get("success") is False

    def test_rejects_no_fields(self):
        with patch("server.physics_tools.get_unreal_connection", return_value=_mock_conn()):
            r = physics_tools.set_constraint_motor("C1")
        assert r.get("success") is False


class TestSpawnPhysicsVolume:
    def test_minimal(self):
        with patch("server.physics_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            physics_tools.spawn_physics_volume("WaterVol")
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload == {"name": "WaterVol"}

    def test_water_with_friction(self):
        with patch("server.physics_tools.get_unreal_connection", return_value=_mock_conn()) as mock_ue:
            physics_tools.spawn_physics_volume(
                "WaterVol",
                location=[0, 0, 100],
                scale=[5, 5, 1],
                terminal_velocity=400.0,
                priority=2.0,
                water_volume=True,
                fluid_friction=0.5,
            )
        payload = mock_ue.return_value.send_command.call_args[0][1]
        assert payload["water_volume"] is True
        assert payload["fluid_friction"] == 0.5
        assert payload["scale"] == [5, 5, 1]

    def test_rejects_negative_terminal(self):
        with patch("server.physics_tools.get_unreal_connection", return_value=_mock_conn()):
            r = physics_tools.spawn_physics_volume("WaterVol", terminal_velocity=-1.0)
        assert r.get("success") is False

    def test_rejects_negative_friction(self):
        with patch("server.physics_tools.get_unreal_connection", return_value=_mock_conn()):
            r = physics_tools.spawn_physics_volume("WaterVol", fluid_friction=-0.1)
        assert r.get("success") is False
